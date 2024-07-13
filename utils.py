import shutil
import csv
import datetime
import json
import os
import shutil
import pandas as pd
import isodate
from tqdm import tqdm

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from openai import OpenAI
from youtube_transcript_api import YouTubeTranscriptApi

from pandas.errors import EmptyDataError

STATUS_FILE = 'status.csv'
RESPONSES_DIR = 'responses' 
ANALYSIS_DIR = 'analysis'
BACKUP_DIR = 'backup'

# status.csv columns and answers
ID = 'id'
CITY = 'city'
WAS_CRAWLED = 'was_crawled'
WAS_ANALYZED = 'was_analyzed'
NO = 'no'
YES = 'yes'
SKIP = 'skip'


import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


def create_backup(csv_file):
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
    
    backup_file = os.path.join(
        BACKUP_DIR,
        f"{csv_file}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.bak"
        )
    try:
        shutil.copy(csv_file, backup_file)
    except FileNotFoundError:
        print(f"No file to back up.")


class ChannelCrawler:
    
    """Runs YouTube APIs on a daily basis as much as quota allows. 
    Status is stored in status.csv file with columns: 'id', 'city' `was_crawled`, 'was_analyzed'. 
    
    Each day, at class init, a status file is read, and line by line determines what still needs 
    to be crawled. It then stores responses in a response json file in directory 'responses'. 
    If it reaches limit, (i.e. API gives exception), then it stops crawling. 
    The status.csv file is then updated.
    """
    youtube = build('youtube', 'v3', developerKey=os.getenv('YT_API_KEY'))

    def __init__(self, csv_file=STATUS_FILE):
        self.csv_file = csv_file
        self.df = self.load_status_file(self.csv_file)
        
        if not os.path.exists(RESPONSES_DIR):
            os.makedirs(RESPONSES_DIR)
    
    @staticmethod
    def load_status_file(csv_file):
        try:
            return pd.read_csv(csv_file)
        except FileNotFoundError:
            print(f"File {csv_file} not found. Creating a new one.")
            df = pd.read_excel('assets/cities_to_collect.xlsx')
            df = df[['ObligorId', 'extracted_issuer']]
            df.rename(columns={'ObligorId': ID, 'extracted_issuer': CITY}, inplace=True)
            df[WAS_CRAWLED] = ''
            df[WAS_ANALYZED] = ''
            df.to_csv(STATUS_FILE, index=False)
            return df
    
    def save_csv(self):
        create_backup(self.csv_file)        
        self.df.to_csv(self.csv_file, index=False)
    
    def search_one(self, search_query):
        # Search for videos matching the query
        request = self.youtube.search().list(
            q=search_query,
            part="snippet",   # this retrieves basic information about the channel
            type="channel",
            maxResults=5
        )
        response = request.execute()
        return response
    
    def crawl(self, unique_id, city):
                    
        try:
            responses = []
            for query in ['town', 'city']:
                search_query = f"{query} of {city} florida"
                response = self.search_one(search_query)
                responses.append(response)
                
            with open(os.path.join(RESPONSES_DIR,f'{unique_id}.json'), 'w') as f:
                json.dump(responses, f, indent=4)
            
            return True
        except HttpError as e:
            if e.resp.status == 403:
                error_response = json.loads(e.content)
                error_reason = error_response["error"]["errors"][0]["reason"]
                if error_reason == "quotaExceeded":
                    print("Quota exceeded. Stopping crawling.")
                    return False
            return False
    
    def start(self):
        for index, row in tqdm(self.df.iterrows()):
            if row[WAS_CRAWLED] != YES:
                unique_id = row[ID]
                city = row[CITY]
                if self.crawl(unique_id, city):
                    self.df.at[index, WAS_CRAWLED] = YES
                else:
                    break
                self.save_csv()
        self.save_csv()
        
        
class ChannelAnalyzer:
    
    """
    Loads status.csv file and then analyzes the newly crawled cities 
    (where 'was_crawled' == 'yes' and 'was_analyzed' == 'no')
    
    The analysis loads a respective json file with responses, and creates a DataFrame 
    with column `is_official`, then save this to a csv file named with unique city id, 
    all in folder named 'analysis'.
    """
    
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    # Set your API key here
    client = OpenAI(api_key=openai_api_key)
    
    def __init__(self, csv_file=STATUS_FILE):
        self.csv_file = csv_file
        self.status_df = pd.read_csv(self.csv_file)
        
        if not os.path.exists(ANALYSIS_DIR):
            os.makedirs(ANALYSIS_DIR)

    def save_status(self):
        self.status_df.to_csv(self.csv_file, index=False)

    def is_official(self, blurb):  
        
            chat_history =[{"role": "system", "content": "Your job will be to analyze short prompts \
            comprised of title and description of YouTube channels to asses whether the channel \
            is official town or city you tube channel. You answer 'Yes' or 'No' only"}]
            
            chat_history.append({"role": "user", "content": blurb})

            reply = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=chat_history
                )

            reply_message = reply.choices[0].message
        
            return reply_message.content.lower()  # this will always return 'yes' or 'no'
    
    def get_smaller_response(self, response):
        # Process the search results
        smaller_response = []
        for item in response.get("items", []):
            channel_id = item["id"]["channelId"]
            channel_title = item["snippet"]["title"]
            channel_description = item["snippet"]["description"]
            
            result = {
                "channel_id": channel_id,
                "channel_title": channel_title,
                "channel_description": channel_description
            }
            smaller_response.append(result)
        return smaller_response
    
    def analyze(self, unique_id):
        try:
            with open(os.path.join(RESPONSES_DIR, f'{unique_id}.json'), 'r') as f:
                responses = json.load(f)
                
            rows = []
            for response in responses:  # there will be two, one for town and one for city
                smaller_response = self.get_smaller_response(response)
                for item in smaller_response:
                    blurb = f"channel title is: {item['channel_title']} and \
                        channel description is: {item['channel_description']}"
                        
                    is_official = self.is_official(blurb)
                    item.update({'is_official': is_official})
                    rows.append(item)
                    
                    # do not do this anymore, let's analyze all responses, since some might be official but not from town
                    # we might need to go back and re-analyze some responses
                    # if is_official == YES:  # no need to analyze further
                    #     break
                
            df = pd.DataFrame(rows)
                
            # Save the analysis DataFrame to a CSV file named with the unique city id
            df.to_csv(os.path.join(ANALYSIS_DIR,f'{unique_id}.csv'), index=False)
            
        except FileNotFoundError:
            print(f"File {RESPONSES_DIR}/{unique_id}.json not found.")

    def start(self):
        for index, row in tqdm(self.status_df.iterrows()):
            if row[WAS_CRAWLED] == YES and pd.isna(row[WAS_ANALYZED]):
                try:
                    unique_id = row[ID]
                    self.analyze(unique_id)
                    self.status_df.at[index, WAS_ANALYZED] = YES
                except Exception as e:
                    print(e)
                    self.status_df.at[index, WAS_ANALYZED] = e
                self.save_status()
                
        self.save_status()
    
    def print_result(self, result):
        print(f"Channel ID: {result['channel_id']}")
        print(f"Title: {result['channel_title']}")
        print(f"Description: {result['channel_description']}")
        print("-" * 40)
        print("\n")
        

def aggregate_analysis_files(crawler, output_file):
    """
    For each city, takes analyzed CSV responses, looks only for the ones ChatGPT marked as yes, and combines them into one row.
    Creates a new csv: aggregated_analysis.csv.
    
    Args:
        crawler (_type_): _description_
        output_file (_type_): _description_
    """
    
    dfs = []

    for filename in os.listdir(ANALYSIS_DIR):
        if filename.endswith('.csv'):
            
            city_id = filename.split('.')[0]
            file_path = os.path.join(ANALYSIS_DIR, filename)
                    
            try:  
                df = pd.read_csv(file_path)
                
                # first remove all but `yes` responses
                df = df[df['is_official'] == 'yes']
                
                # then remove the duplicates
                df = df.drop_duplicates()
                
                # then remove the `is_official` column
                df = df.drop(columns=['is_official'])
                
                # then replace the channel_id with the URL of the channel
                df['URL'] = df['channel_id'].apply(lambda x: f"https://www.youtube.com/channel/{x}")
                
                # drop the channel_id column
                df = df.drop(columns=['channel_id'])
                
                # finally, flatten the DataFrame into a single row
                new_df = pd.DataFrame(df.values.flatten()).T
                
                # rename the columns
                new_df.columns = [f"{col}_{i+1}" for i in range(len(df)) for col in df.columns]
                
                # then add a column with the city_id
                new_df['city_id'] = city_id
                
                # Move 'city_id' to the first column
                new_df.insert(0, 'city_id', new_df.pop('city_id'))
                
            except EmptyDataError:
                print(f"Error reading {file_path}. Skipping it.")
                continue

            dfs.append(new_df)
            
    combined_df = pd.concat(dfs, ignore_index=True)

    # add a city name by joining with the status file
    combined_df = crawler.df.merge(combined_df, left_on='id', right_on='city_id', how='left')

    combined_df.drop(['city_id', 'was_crawled', 'was_analyzed'], axis=1, inplace=True)
    
    combined_df.rename(columns={'id': 'ObligorId', 'city': 'extracted_issuer'}, inplace=True)
    
    # add county name
    df_orig = pd.read_excel('assets/cities_to_collect.xlsx')
    df_orig = df_orig[['ObligorId', 'county']]
    
    combined_df = combined_df.merge(df_orig, left_on='ObligorId', right_on='ObligorId', how='left')
    
    combined_df = move_col(combined_df, 'county', 2)
    
    combined_df.to_excel(output_file, index=False, engine='openpyxl')


def move_col(df, col_to_move, new_index):
    cols = df.columns.tolist()
    cols.insert(new_index, cols.pop(cols.index(col_to_move)))
    return df[cols]


class Channel(object):
    
    youtube = build('youtube', 'v3', developerKey=os.getenv('YT_API_KEY'))
    
    def __init__(self, channel_id):
        self.channel_id = channel_id
        self.url = f'https://www.youtube.com/channel/{self.channel_id}'
        self.videos = []

    def get_channel_username(self):
        # TODO 
        pass
        
    def get_videos(self):
        
        videos = []
        next_page_token = None

        while True:
            request = self.youtube.search().list(
                part="snippet",
                channelId=self.channel_id,
                maxResults=50,
                pageToken=next_page_token,
                order="date",
                type="video",
                # eventType="live"  # This filters for live streams only, doesn't work
            )
            response = request.execute()

            for item in response.get('items', []):
                video_info = {
                    "video_id": item['id']['videoId'],
                    "title": item['snippet']['title'],
                    "description": item['snippet']['description'],
                    "published_at": item['snippet']['publishedAt']
                }
                videos.append(video_info)

            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break

        self.videos = videos
        
        self.export_video_list()

    def export_video_list(self):
        filepath = os.path.join('channels', self.channel_id, 'videos.json')
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        
        # Export to JSON file
        with open(filepath, 'w') as json_file:
            json.dump(self.videos, json_file, indent=4)

    def extract_all(self):
        # TODO need to add a status file here so I can keep track of what was done
        # and in case there is an issue, like quota exceeded, I can pick up where I left off
        for video in self.videos:
            video_id = video['video_id']
            video_info = VideoInfo(video_id)
            video_info.get_all_video_info()

class VideoInfo(object):
    """
    All relevant video info and transcript.
    
    YouTube video_id is what comes after 'v=' in URL: https://www.youtube.com/watch?v=5AIBek1jhfE
    so in this case, the ID is 5AIBek1jhfE.
    """
    youtube = build('youtube', 'v3', developerKey=os.getenv('YT_API_KEY'))
    
    def __init__(self, video_id):
        self.id = video_id
        self.url = f'https://www.youtube.com/watch?v={self.id}'
            
    @staticmethod
    def convert_duration(duration):
    # Convert ISO 8601 duration to minutes
        parsed_duration = isodate.parse_duration(duration)
        return parsed_duration.total_seconds() / 60

    def get_only_video_info(self):
        # Get video details
        request = self.youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=self.id
        )
        response = request.execute()

        if "items" not in response or len(response["items"]) == 0:
            print("Video not found.")
            return None

        video = response["items"][0]

        self.title = video["snippet"]["title"]
        self.description = video["snippet"]["description"]
        self.upload_date = video["snippet"]["publishedAt"]
        self.duration = self.convert_duration(video["contentDetails"]["duration"])
        self.views = video["statistics"].get("viewCount", 0)
        self.likes = video["statistics"].get("likeCount", 0)
        self.channel_id = video["snippet"]["channelId"]
        self.channel_title = video["snippet"]["channelTitle"]
        
    # Function to get transcript
    def get_only_transcript(self):
        
        try:
            # Fetch the transcript
            transcript = YouTubeTranscriptApi.get_transcript(self.id)
            
            # Combine transcript segments into one text
            transcript_text = " ".join([entry['text'] for entry in transcript])
            
            self.transcript = transcript_text
            
            filepath = os.path.join('channels', self.channel_id, 'transcripts', f'transcript_{self.id}.csv')
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Write the string to the CSV file
            with open(filepath, mode='w', newline='') as file:
                writer = csv.writer(file)
                
                # Write the string as a single row
                writer.writerow([transcript])

            # print(f"String saved to {filepath}")
            return True, None
        
        except Exception as e:
            print('Could not get transcript for video: ', self.id)
            self.transcript = None
            print(e)
            return False, e
            

    def export(self):
        # Extract relevant details
        video_info_and_transcript = {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "upload_date": self.upload_date,
            "duration": self.duration,
            "views": self.views,
            "likes": self.likes,
            "channel_id": self.channel_id,
            "channel_title": self.channel_title,
            "url": self.url,
            "transcript_success": self.transcript_success,
            "transcript_error": self.transcript_error,
            'transcript': self.transcript
        }
        
        filepath = os.path.join('channels', self.channel_id, 'videos', f'{self.id}.json')
        
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
        # Write the dictionary to a JSON file
        with open(filepath, 'w') as json_file:
            json.dump(video_info_and_transcript, json_file, indent=4)

        # print(f"Dictionary saved to {filepath}")

    def get_all_video_info(self):
        self.get_only_video_info()
        self.transcript_success, self.transcript_error = self.get_only_transcript()
        self.export()

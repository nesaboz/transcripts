from youtube_transcript_api import YouTubeTranscriptApi
import csv
import json
from googleapiclient.discovery import build
import isodate

api_key = 'AIzaSyBHJkj-ghB84lI8b3dX5QGhjy7U3N0CsRU'

# Set up the API key and service
youtube = build('youtube', 'v3', developerKey=api_key)


# Function to get transcript
def get_transcript(video_id):

    try:
        # Fetch the transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Combine transcript segments into one text
        transcript_text = " ".join([entry['text'] for entry in transcript])
        
        return transcript_text
    except Exception as e:
        return str(e)
    

def get_video_info(video_id):
    # Get video details
    request = youtube.videos().list(
        part="snippet,contentDetails,statistics",
        id=video_id
    )
    response = request.execute()

    if "items" not in response or len(response["items"]) == 0:
        print("Video not found.")
        return None

    video = response["items"][0]

    # Extract relevant details
    video_info = {
        "vid_id": video_id,
        "vid_title": video["snippet"]["title"],
        "vid_desc": video["snippet"]["description"],
        "vid_upload_date": video["snippet"]["publishedAt"],
        "vid_length_min": convert_duration(video["contentDetails"]["duration"]),
        "vid_views": video["statistics"].get("viewCount", 0),
        "vid_likes": video["statistics"].get("likeCount", 0),
        "channel_id": video["snippet"]["channelId"],
        "channel_title": video["snippet"]["channelTitle"],
    }

    return video_info


def convert_duration(duration):
    # Convert ISO 8601 duration to minutes
    
    parsed_duration = isodate.parse_duration(duration)
    return parsed_duration.total_seconds() / 60

    
def save_transcript_to_file(filename, transcript):
    # Write the string to the CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        
        # Write the string as a single row
        writer.writerow([transcript])

    print(f"String saved to {filename}")
    
    
def save_metadata_to_file(filename, video_info):

    # Write the dictionary to a JSON file
    with open(filename, 'w') as json_file:
        json.dump(video_info, json_file, indent=4)

    print(f"Dictionary saved to {filename}")
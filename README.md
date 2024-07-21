# Florida free-speech project

Get transcripts from Town Hall meetings in Florida cities and towns for the research purposes. 

From list of towns in Florida I used YouTube API to first search for official town/city channel, and asked ChatGPT to evaluate if the channel seems official based on a channel title and description. I then called YouTube API to get all videos from the channel and then get transcripts for each video.

## API developer keys

For code to work one needs to have YouTube developer API key and OpenAI key. These should be secret and should not be commited to GitHub which is why I use these as environment variables and not hard-coded directly.

All one have to do once is:
- find API keys (for example follow [this](https://docs.themeum.com/tutor-lms/tutorials/get-youtube-api-key/) and [this](https://whatsthebigdata.com/how-to-get-openai-api-key/), or many more other online tutorials).
- set them up as env variables by creating a file named ".env" in the project root (or Google Drive root) that looks like this (replace XYZ1 and XYZ2 with your secret keys, and note not to use quotation marks):

```text
YT_API_KEY=XYZ1
OPENAI_API_KEY=XYZ2
```

I use [dotenv](https://pypi.org/project/python-dotenv/) library to create env variables from this file 

This .env file should never be shared and never be commited to the GitHub (it is also present in .gitignore).

## Data 

If using Google Colab data folder is shared via [`PN`](https://drive.google.com/drive/folders/1Y40dEWaFAvuKVPDPwa8cK1Tj8_6O5Bw4?usp=sharing) folder. You must create a shortcut to this folder and place it in the root of your Google Drive.

If using data locally, create folder `data` and place it in a root of a cloned repo.

## Run code

Repo assumes runing both in the local environment and Google Colab. Code is already suited for both.

Watch [screencast](https://drive.google.com/file/d/1YnyMtkF-NpkP7jvEpkkfNuBSYYTaiwEg/view?usp=share_link) if this is first-time running.

Google Colab: run [link](https://colab.research.google.com/github/nesaboz/transcripts/blob/main/main.ipynb). 

Locally: run `main.ipynb` and refer to `utils.py` for all lower level code. 

## Appendix

Some transcripts are unavailable in which case transcript is empty (API gives following error):

```text
Could not get transcript for video:  XYZ

Could not retrieve a transcript for the video https://www.youtube.com/watch?v=XYZ This is most likely caused by:

Subtitles are disabled for this video

If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!
```

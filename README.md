# Florida free-speech project

Get transcripts from Town Hall meetings in Florida cities and towns for the research purposes. 

From list of towns in Florida I used YouTube API to first search for official town/city channel, and asked ChatGPT to evaluate if the channel seems official based on a channel title and description. I then called YouTube API to get all videos from the channel and then get transcripts for each video.

## Appendix

Some transcripts are unavailable in which case transcript is empty (API gives following error):

```text
Could not get transcript for video:  XYZ

Could not retrieve a transcript for the video https://www.youtube.com/watch?v=XYZ This is most likely caused by:

Subtitles are disabled for this video

If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!
```

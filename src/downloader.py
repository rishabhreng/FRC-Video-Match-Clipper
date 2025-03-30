import os


# Download YouTube VOD
def download_youtube_vod(video_output_name, YOUTUBE_URL):
    if not os.path.exists(video_output_name):
        import yt_dlp

        ydl_opts = {
            "outtmpl": video_output_name,
            "merge_output_format": "mp4",
            "n_threads": 4,  # Use 4 threads for maximum speed
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([YOUTUBE_URL])

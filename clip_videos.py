import os
import argparse

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Download, clip, and upload FRC match videos automatically from full stream videos. Can be used for sharing or uploading to The Blue Alliance. Requires a Google Cloud Console OAuth client_secrets.json file (just paste it in the same directory as this file) and a TBA API key for uploading."
    )
    parser.add_argument(
        "-y",
        "--youtube-url",
        type=str,
        required=True,
        help="URL of the YouTube video to download",
    )
    parser.add_argument(
        "-e", "--event-key", type=str, required=True, help="TBA event key"
    )
    parser.add_argument(
        "-s",
        "--suffix",
        type=str,
        required=False,
        help="Suffix for the video and clips",
    )
    parser.add_argument(
        "-tba",
        "--tba-key",
        type=str,
        required=False,
        help="TBA API key (if not set, will use TBA_API_KEY environment variable)",
    )

    args = parser.parse_args()

    YOUTUBE_URL = args.youtube_url
    EVENT_KEY = args.event_key
    suffix = args.suffix if args.suffix else ""
    clips_folder = f"matches_{EVENT_KEY}_{suffix}"
    video_path = f"{EVENT_KEY}_{suffix}.mp4"

    TBA_API_KEY = args.tba_key if args.tba_key else os.getenv("TBA_API_KEY")

    # Downloads VOD if it's not already downloaded
    print("Downloading VOD...")
    from src.downloader import download_youtube_vod

    download_youtube_vod(video_output_name=video_path, YOUTUBE_URL=YOUTUBE_URL)
    print("VOD downloaded!")

    # Clips and uploads the match videos
    clip = input("Do you want to clip the videos? (y/n): ")
    if clip == "y":
        print("Clipping matches...")
        from src.clipper import clip_videos

        clip_videos(video_input_path=video_path, clips_output_folder=clips_folder)
        print("All matches clipped!")

    upload = input("Do you want to upload the (existing) clips to YouTube? (y/n): ")
    if upload == "y":
        print("Uploading clips to YouTube...")
        from src.uploader import upload_clips

        upload_clips(
            folder_input_path=clips_folder, event_key=EVENT_KEY, tba_key=TBA_API_KEY
        )
        print("All clips uploaded! Done!")

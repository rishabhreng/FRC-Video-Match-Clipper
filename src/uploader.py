from google.auth.transport.requests import Request
import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import os
from tqdm import tqdm
import tbapy
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# Define the scopes required for managing playlists
SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


# Authenticate and build the YouTube API client
# NOTE: ensure that you have a client_secrets.json available from Google Cloud Console
#       and that you have enabled the YouTube Data API v3 for your project
# NOTE: the first time you run this script, it will open a browser window requesting
#       permission to manage your YouTube account. You should allow this permission.
#       Ensure that you specify a test user account for this purpose in the Google Cloud Console.
#       This account will be the uploader.
def get_youtube_client():
    creds = None
    # The file 'token.pickle' stores the user's access and refresh tokens.
    # It is created automatically when the authorization flow completes for the first time.
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "client_secrets.json", SCOPES
            )
            creds = flow.run_local_server(
                port=0
            )  # Will prompt user for authorization if necessary
        # Save the credentials for the next run
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    # Build the YouTube client
    youtube = build("youtube", "v3", credentials=creds)
    return youtube


def create_playlist(youtube, title, description):
    # Check if a playlist with the same title already exists
    try:
        existing_playlists = youtube.playlists().list(
            part="snippet",
            mine=True
        ).execute()

        for playlist in existing_playlists.get("items", []):
            if playlist["snippet"]["title"] == title:
                print(f"Playlist already exists: {title}")
                return playlist["id"]

        # If no playlist with the same title exists, create a new one
        playlist_request = youtube.playlists().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                },
                "status": {
                    "privacyStatus": "public",  # Can be "private", "public", or "unlisted"
                },
            },
        )
        playlist_response = playlist_request.execute()
        playlist_id = playlist_response["id"]
        print(f"Playlist created successfully: {title}")
        return playlist_id
    except HttpError as e:
        print(f"An error occurred: {e}")
        return None


# Add a video to a playlist
def add_video_to_playlist(youtube, playlist_id, video_id):
    try:
        playlist_item_request = youtube.playlistItems().insert(
            part="snippet",
            body={
                "snippet": {
                    "playlistId": playlist_id,
                    "resourceId": {
                        "kind": "youtube#video",
                        "videoId": video_id,
                    },
                }
            },
        )
        playlist_item_request.execute()
        print(f"Video {video_id} added to playlist {playlist_id}")
    except HttpError as e:
        print(f"An error occurred while adding video {video_id} to playlist: {e}")


# Upload a video and return the video ID
def upload(
    youtube,
    video_path,
    title=["FRC Match Video"],
    description="FRC Video",
    tags=["FRC"],
    category_id="24",
    privacy_status="public",
):
    request_body = {
        "snippet": {
            "categoryId": category_id,
            "description": description,
            "title": title,
            "tags": tags,
        },
        "status": {
            "privacyStatus": privacy_status,
        },
    }

    media_file = MediaFileUpload(video_path)

    try:
        response_upload = (
            youtube.videos()
            .insert(
                part="snippet,status",
                body=request_body,
                media_body=media_file,
            )
            .execute()
        )
        video_id = response_upload.get("id")
        print(f"Video uploaded successfully: {video_id}")
        return video_id
    except HttpError as e:
        print(f"An error occurred while uploading the video: {e}")
        return None


def upload_clips(folder_input_path, event_key, tba_key):
    # Get all video files in folder
    folder_path = folder_input_path
    video_files = [f for f in os.listdir(folder_path) if f.endswith(".mp4")]

    tba = tbapy.TBA(tba_key).event(event_key, simple=True)
    title_prefix = str(tba.get("year")) + " " + tba.get("name")

    # Authenticate YouTube API client
    youtube = get_youtube_client()

    # Create a playlist for the event if it doesn't exist
    playlist_title = title_prefix
    playlist_description = "Matches for " + title_prefix
    playlist_id = create_playlist(youtube, playlist_title, playlist_description)

    if not playlist_id:
        print("Failed to create playlist, exiting.")
        exit(1)

    # Upload videos and add them to the playlist
    if not os.path.exists(f"{folder_path}/uploaded.txt"):
        
        with open(f"{folder_path}/uploaded.txt", "w"):
            pass
    with open(f"{folder_path}/uploaded.txt", "r+") as f:
        matches_data = f.readlines()
        f.seek(0)
        for video_file in tqdm(video_files):
            if any(video_file in match for match in matches_data):
                print(f"Skipping {video_file} as it has already been uploaded.")
                continue
            match_id = video_file.split("_")[1]
            video_title = f'{title_prefix}: {match_id}'
            video_path = os.path.join(folder_path, video_file)

            # Upload video and get video ID
            video_id = upload(youtube, video_path, title=video_title)
            f.write(video_path + "\n")

            # Add the uploaded video to the playlist
            add_video_to_playlist(youtube, playlist_id, video_id)
            # time.sleep(5)
        f.truncate()
    print("All videos uploaded and added to playlist successfully.")

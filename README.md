# Download, clip, and upload FRC match videos automatically from full stream videos. Can be used for sharing or uploading to The Blue Alliance. 
- Easy to use in command terminal!
- Requires a Google Cloud Console OAuth _client_secrets.json_ file (just paste it in the same directory as this file) and a TBA API key for uploading.
- This uses OCR to run more quickly, so you might want to have a GPU on hand to run this script more efficiently.
- This project was created with Python 3.10.


How to run:
- Create a virtual environment with venv or conda.
- Have on hand your Youtube stream URL and the event key (e.g. 2025cmptx) as specified on The Blue Alliance or FirstInspires.
- Example with venv:
```bash
git clone https://github.com/rishabhreng/FRC-Video-Match-Clipper
python -m venv clip
pip install -r requirements.txt

./clip/Scripts/activate.bat
# do this if you want to see all available parameters
python clip_videos.py -h 

python clip_videos.py -y [YOUTUBE_LINK] -e [EVENT_KEY] -s [suffix, optional] -tba_key [optional, necessary to upload]
```

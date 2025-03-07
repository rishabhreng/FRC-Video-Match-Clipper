import cv2
import easyocr
import subprocess
import re
from datetime import timedelta
from PIL import Image
import os

# Initialize OCR reader
reader = easyocr.Reader(["en"], gpu=True)


def clip_videos(video_input_path, clips_output_folder):
    VIDEO_PATH = video_input_path
    cap = cv2.VideoCapture(VIDEO_PATH)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Skip settings
    frame_skip_search_frames = int(fps * 5)  # Skip 5 seconds
    frame_skip_record_frames = int(fps * 2)  # Skip 2 seconds
    frame_skip_seek_frames = int(fps * 15)  # Skip 15 seconds

    recording = False
    start_time_sec = None
    match_number = None

    frame_count = 0

    os.makedirs(clips_output_folder, exist_ok=True)
    output_dir = clips_output_folder

    while cap.isOpened():
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
        ret, frame = cap.read()
        if not ret:
            break

        frame_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        cropped_top = gray[: int(gray.shape[0] * 0.3), :]
        # Image.fromarray(cropped_top).save("output.png")
        result = reader.readtext(cropped_top, detail=0)
        detected_texts = [r for r in result]

        # Detect match number
        skip = False
        for text in detected_texts:
            if "Test" in text:
                skip = True
            if "Qualification" in text or "Match" in text:
                match_number = (
                    text.replace("Qualification", "").replace("Match", "").strip()
                )

        # Detect auto period countdown (start of match)
        if not skip and not recording:
            for text in detected_texts:
                match = re.search(r"0:(\d{2})", text)
                if match:
                    seconds_remaining = int(match.group(1))
                    if 1 <= seconds_remaining <= 15:
                        start_time_sec = max(
                            0, frame_time - (15 - seconds_remaining + 7.5)
                        )
                        recording = True
                        print(
                            f"❗Match {match_number} started at {timedelta(seconds=start_time_sec)}"
                        )
                        break

        # Jump exactly 2:50 after start to find end of match
        if recording:
            frame_count = int((start_time_sec + 170) * fps)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                frame_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                cropped_top = gray[: int(gray.shape[0] * 0.3), :]
                # Image.fromarray(cropped_top).save("output.png")
                result = reader.readtext(cropped_top, detail=0)

                if (
                    "0:00" in result
                    or "0:0O" in result
                    or "0:O0" in result
                    or "0:OO" in result
                    or "O:00" in result
                    or "O:0O" in result
                    or "O:O0" in result
                    or "O:OO" in result
                    or ("Match Under" in result and "Review" in result)
                    or ("Match Under Review" in result)
                ):
                    break

            # Fast-seek until scoreboard appears
            while cap.isOpened():
                frame_count += frame_skip_seek_frames
                cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count)
                ret, frame = cap.read()
                if not ret:
                    break

                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                cropped_top = gray[: int(gray.shape[0] * 0.3), :]
                # Image.fromarray(cropped_top).save("output.png")
                result = reader.readtext(cropped_top, detail=0)

                if any(
                    "WINNER" in text.upper() or "TIE" in text.upper() for text in result
                ):
                    scoreboard_time = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                    print(
                        f"✅ Scoreboard found at {timedelta(seconds=scoreboard_time)}"
                    )
                    break

            # Clip both segments and join them
            output_filename = f"{output_dir}/match_{match_number}.mp4"

            segment1 = f"{output_dir}/segment1.mp4"
            segment2 = f"{output_dir}/segment2.mp4"

            # TODO: find optimal codec settings for fastest encoding that is uploadable to YouTube but runs in reasonable time
            # Clip first segment (match only)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    VIDEO_PATH,
                    "-ss",
                    str(start_time_sec),
                    "-to",
                    str(start_time_sec + 165),
                    "-c",
                    "copy",
                    "-avoid_negative_ts",
                    "make_zero",
                    segment1,
                ],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )

            # Clip second segment (scoreboard only)
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    VIDEO_PATH,
                    "-ss",
                    str(scoreboard_time - 20),
                    "-to",
                    str(scoreboard_time + 15),
                    "-c",
                    "copy",
                    "-avoid_negative_ts",
                    "make_zero",
                    segment2,
                ],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )

            # Concatenate segments
            with open(f"{output_dir}/concat_list.txt", "w") as f:
                f.write(f"file '{segment1.removeprefix(output_dir + '/')}'\n")
                f.write(f"file '{segment2.removeprefix(output_dir + '/')}'\n")

            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    f"{output_dir}/concat_list.txt",
                    "-c",
                    "copy",
                    "-avoid_negative_ts",
                    "make_zero",
                    output_filename,
                ],
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )

            if os.path.exists(segment1):
                os.remove(segment1)
            if os.path.exists(segment2):
                os.remove(segment2)
            if os.path.exists(f"{output_dir}/concat_list.txt"):
                os.remove(f"{output_dir}/concat_list.txt")
            print(f"✅ Saved match video: {output_filename}")

            recording = False

        frame_count += (
            frame_skip_search_frames if not recording else frame_skip_record_frames
        )

    cap.release()
    cv2.destroyAllWindows()

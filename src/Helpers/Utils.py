import os
import re
import random
import base64
import shutil
import tempfile
import asyncio
import requests

from typing import List, Set, Any, Optional
from bs4 import BeautifulSoup
from moviepy.video.io.VideoFileClip import VideoFileClip
import imgbbpy


class Utils:
    def __init__(self, log: Any, config: Any) -> None:
        self.log = log
        self.config = config

    @staticmethod
    async def sleep(ms: int) -> None:
        await asyncio.sleep(ms / 1000)

    def fetch(self, url: str) -> Optional[dict]:
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.log.error(f"[ERROR] [fetch] {e}")
            return None

    def fetch_buffer(self, url: str) -> bytes:
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            self.log.error(f"[ERROR] [fetch_buffer] {e}")
            return b""

    @staticmethod
    def is_truthy(value: Any) -> bool:
        return bool(value)

    def readdir_recursive(self, directory: str) -> List[str]:
        results: List[str] = []
        for root, _, files in os.walk(directory):
            for file in files:
                results.append(os.path.join(root, file))
        return results

    def find_and_delete_all(self, filename: str, search_path: str = ".") -> int:
        deleted_count = 0
        for root, _, files in os.walk(search_path):
            if filename in files:
                file_path = os.path.join(root, filename)
                try:
                    os.remove(file_path)
                    self.log.info(f"[Deleted] {file_path}")
                    deleted_count += 1
                except Exception as e:
                    self.log.error(
                        f"[ERROR] [find_and_delete_all] Failed to delete {file_path}: {e}"
                    )
        if deleted_count == 0:
            self.log.info("[info] No matching files found.")
        return deleted_count

    @staticmethod
    def to_small_caps(text: str) -> str:
        map_small: dict[str, str] = {
            "a": "ᴀ",
            "b": "ʙ",
            "c": "ᴄ",
            "d": "ᴅ",
            "e": "ᴇ",
            "f": "ꜰ",
            "g": "ɢ",
            "h": "ʜ",
            "i": "ɪ",
            "j": "ᴊ",
            "k": "ᴋ",
            "l": "ʟ",
            "m": "ᴍ",
            "n": "ɴ",
            "o": "ᴏ",
            "p": "ᴘ",
            "q": "Q",
            "r": "ʀ",
            "s": "ꜱ",
            "t": "ᴛ",
            "u": "ᴜ",
            "v": "ᴠ",
            "w": "ᴡ",
            "x": "x",
            "y": "ʏ",
            "z": "ᴢ",
        }
        return "".join(map_small.get(c.lower(), c) for c in text)

    @staticmethod
    def buffer_to_base64(buffer: bytes) -> str:
        return base64.b64encode(buffer).decode("utf-8")

    def webp_to_mp4(self, webp: bytes) -> bytes:
        try:

            def request(
                form_data: dict, file_id: Optional[str] = None
            ) -> BeautifulSoup:
                url = (
                    f"https://ezgif.com/webp-to-mp4/{file_id}"
                    if file_id
                    else "https://ezgif.com/webp-to-mp4"
                )
                response = requests.post(url, files=form_data)
                return BeautifulSoup(response.text, "html.parser")

            files = {"new-image": ("upload.webp", webp, "image/webp")}
            soup1 = request(files)
            file_id = soup1.find("input", {"name": "file"})["value"]

            files = {
                "file": (file_id, "image/webp"),
                "convert": "Convert WebP to MP4!",
            }
            soup2 = request(files, file_id)
            video_url = (
                "https:"
                + soup2.find("div", id="output")
                .find("video")
                .find("source")["src"]
            )
            return requests.get(video_url).content

        except Exception as e:
            self.log.error(f"[ERROR] [webp_to_mp4] {e}")
            return b""

    @staticmethod
    def extract_numbers(content: str) -> List[int]:
        return [max(int(n), 0) for n in re.findall(r"-?\d+", content)]

    @staticmethod
    def get_random_int(min_val: int, max_val: int) -> int:
        return random.randint(min_val, max_val)

    @staticmethod
    def get_random_float(min_val: float, max_val: float) -> float:
        return random.uniform(min_val, max_val)

    @staticmethod
    def get_random_item(array: List[Any]) -> Any:
        return random.choice(array)

    @staticmethod
    def get_random_items(array: List[Any], count: int) -> List[Any]:
        return random.choices(array, k=count)

    @staticmethod
    def get_urls(text: str) -> Set[str]:
        return set(re.findall(r"https?://[^\s]+", text))

    def gif_to_mp4(self, gif: bytes) -> bytes:
        temp_dir = tempfile.mkdtemp()
        gif_path = os.path.join(temp_dir, "input.gif")
        mp4_path = os.path.join(temp_dir, "output.mp4")

        try:
            with open(gif_path, "wb") as f:
                f.write(gif)

            clip = VideoFileClip(gif_path)
            clip.write_videofile(mp4_path, codec="libx264", logger=None)

            with open(mp4_path, "rb") as f:
                return f.read()

        except Exception as e:
            self.log.error(f"[ERROR] [gif_to_mp4] {e}")
            return b""

        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @staticmethod
    def capitalize(s: str) -> str:
        return s.capitalize() if s else s

    def img_to_url(self, img_path: str) -> Optional[str]:
        try:
            client = imgbbpy.SyncClient(self.config.imgbb_key)
            image = client.upload(file=img_path)
            return image.url
        except Exception as e:
            self.log.error(f"[ERROR] [img_to_url] {e}")
            return None

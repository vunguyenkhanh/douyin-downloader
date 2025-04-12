#!/usr/bin/env python
# -*- coding: utf-8 -*-


import os
import json
import time
import requests
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
from typing import List, Optional
from pathlib import Path
# import asyncio  # Temporarily commented out
# import aiohttp  # Temporarily commented out
import logging
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.text import Text
from rich import print as rprint

from apiproxy.douyin import douyin_headers
from apiproxy.common import utils

logger = logging.getLogger("douyin_downloader")
console = Console()

class Download(object):
    def __init__(self, thread=5, music=True, cover=True, avatar=True, resjson=True, folderstyle=True):
        self.thread = thread
        self.music = music
        self.cover = cover
        self.avatar = avatar
        self.resjson = resjson
        self.folderstyle = folderstyle
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            transient=True  # Add this parameter to auto-hide progress bar when complete
        )
        self.retry_times = 3
        self.chunk_size = 8192
        self.timeout = 30

    def _download_media(self, url: str, path: Path, desc: str) -> bool:
        """Generic download method for handling all types of media downloads"""
        if path.exists():
            self.console.print(f"[cyan]⏭️  Skip existing: {desc}[/]")
            return True

        # Replace original download logic with new resume-capable download method
        return self.download_with_resume(url, path, desc)

    def _download_media_files(self, aweme: dict, path: Path, name: str, desc: str) -> None:
        """Download all media files"""
        try:
            # Download video or image collection
            if aweme["awemeType"] == 0:  # Video
                video_path = path / f"{name}_video.mp4"
                if url := aweme.get("video", {}).get("play_addr", {}).get("url_list", [None])[0]:
                    if not self._download_media(url, video_path, f"[Video]{desc}"):
                        raise Exception("Video download failed")

            elif aweme["awemeType"] == 1:  # Image Collection
                for i, image in enumerate(aweme.get("images", [])):
                    if url := image.get("url_list", [None])[0]:
                        image_path = path / f"{name}_image_{i}.jpeg"
                        if not self._download_media(url, image_path, f"[Image {i+1}]{desc}"):
                            raise Exception(f"Image {i+1} download failed")

            # Download music
            if self.music and (url := aweme.get("music", {}).get("play_url", {}).get("url_list", [None])[0]):
                music_name = utils.replaceStr(aweme["music"]["title"])
                music_path = path / f"{name}_music_{music_name}.mp3"
                if not self._download_media(url, music_path, f"[Music]{desc}"):
                    self.console.print(f"[yellow]⚠️  Music download failed: {desc}[/]")

            # Download cover
            if self.cover and aweme["awemeType"] == 0:
                if url := aweme.get("video", {}).get("cover", {}).get("url_list", [None])[0]:
                    cover_path = path / f"{name}_cover.jpeg"
                    if not self._download_media(url, cover_path, f"[Cover]{desc}"):
                        self.console.print(f"[yellow]⚠️  Cover download failed: {desc}[/]")

            # Download avatar
            if self.avatar:
                if url := aweme.get("author", {}).get("avatar", {}).get("url_list", [None])[0]:
                    avatar_path = path / f"{name}_avatar.jpeg"
                    if not self._download_media(url, avatar_path, f"[Avatar]{desc}"):
                        self.console.print(f"[yellow]⚠️  Avatar download failed: {desc}[/]")

        except Exception as e:
            raise Exception(f"Download failed: {str(e)}")

    def awemeDownload(self, awemeDict: dict, savePath: Path) -> None:
        """Download all content for a single post"""
        if not awemeDict:
            logger.warning("Invalid post data")
            return

        try:
            # Create save directory
            save_path = Path(savePath)
            save_path.mkdir(parents=True, exist_ok=True)

            # Build filename
            file_name = f"{awemeDict['create_time']}_{utils.replaceStr(awemeDict['desc'])}"
            aweme_path = save_path / file_name if self.folderstyle else save_path
            aweme_path.mkdir(exist_ok=True)

            # Save JSON data
            if self.resjson:
                self._save_json(aweme_path / f"{file_name}_result.json", awemeDict)

            # Download media files
            desc = file_name[:30]
            self._download_media_files(awemeDict, aweme_path, file_name, desc)

        except Exception as e:
            logger.error(f"Error processing post: {str(e)}")

    def _save_json(self, path: Path, data: dict) -> None:
        """Save JSON data"""
        try:
            with open(path, "w", encoding='utf-8') as f:
                json.dump(data, ensure_ascii=False, indent=2, fp=f)
        except Exception as e:
            logger.error(f"Failed to save JSON: {path}, Error: {str(e)}")

    def userDownload(self, awemeList: List[dict], savePath: Path):
        if not awemeList:
            self.console.print("[yellow]⚠️  No downloadable content found[/]")
            return

        save_path = Path(savePath)
        save_path.mkdir(parents=True, exist_ok=True)

        start_time = time.time()
        total_count = len(awemeList)
        success_count = 0

        # Display download info panel
        self.console.print(Panel(
            Text.assemble(
                ("Download Configuration\n", "bold cyan"),
                (f"Total: {total_count} posts\n", "cyan"),
                (f"Threads: {self.thread}\n", "cyan"),
                (f"Save path: {save_path}\n", "cyan"),
            ),
            title="Douyin Downloader",
            border_style="cyan"
        ))

        with self.progress:
            download_task = self.progress.add_task(
                "[cyan]📥 Batch download progress",
                total=total_count
            )

            for aweme in awemeList:
                try:
                    self.awemeDownload(awemeDict=aweme, savePath=save_path)
                    success_count += 1
                    self.progress.update(download_task, advance=1)
                except Exception as e:
                    self.console.print(f"[red]❌ Download failed: {str(e)}[/]")

        # Display download completion statistics
        end_time = time.time()
        duration = end_time - start_time
        minutes = int(duration // 60)
        seconds = int(duration % 60)

        self.console.print(Panel(
            Text.assemble(
                ("Download Complete\n", "bold green"),
                (f"Success: {success_count}/{total_count}\n", "green"),
                (f"Time taken: {minutes}m {seconds}s\n", "green"),
                (f"Save location: {save_path}\n", "green"),
            ),
            title="Download Statistics",
            border_style="green"
        ))

    def download_with_resume(self, url: str, filepath: Path, desc: str) -> bool:
        """Download method with resume support"""
        file_size = filepath.stat().st_size if filepath.exists() else 0
        headers = {'Range': f'bytes={file_size}-'} if file_size > 0 else {}

        for attempt in range(self.retry_times):
            try:
                response = requests.get(url, headers={**douyin_headers, **headers},
                                     stream=True, timeout=self.timeout)

                if response.status_code not in (200, 206):
                    raise Exception(f"HTTP {response.status_code}")

                total_size = int(response.headers.get('content-length', 0)) + file_size
                mode = 'ab' if file_size > 0 else 'wb'

                with self.progress:
                    task = self.progress.add_task(f"[cyan]⬇️  {desc}", total=total_size)
                    self.progress.update(task, completed=file_size)  # Update progress for resumed download

                    with open(filepath, mode) as f:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                size = f.write(chunk)
                                self.progress.update(task, advance=size)

                return True

            except Exception as e:
                logger.warning(f"Download failed (attempt {attempt + 1}/{self.retry_times}): {str(e)}")
                if attempt == self.retry_times - 1:
                    self.console.print(f"[red]❌ Download failed: {desc}\n   {str(e)}[/]")
                    return False
                time.sleep(1)  # Wait before retry


class DownloadManager:
    def __init__(self, max_workers=3):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def download_with_resume(self, url, filepath, callback=None):
        # Check for partially downloaded file
        file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0

        headers = {'Range': f'bytes={file_size}-'}

        response = requests.get(url, headers=headers, stream=True)
        total_size = int(response.headers.get('content-length', 0))

        mode = 'ab' if file_size > 0 else 'wb'

        with open(filepath, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    if callback:
                        callback(len(chunk))


if __name__ == "__main__":
    pass

"""
Genius Lyrics module (Custom DOM Scraper)
"""

import os
import re
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional

from spotdl.providers.lyrics.base import LyricsProvider
from spotdl.utils.config import GlobalConfig

__all__ = ["Genius"]

class Genius(LyricsProvider):
    """
    Genius lyrics provider class using direct web scraping.
    """

    def __init__(self, access_token: str = None):
        super().__init__()
        self.access_token = access_token
        self.session = requests.Session()

        # Override User-Agent to prevent bot blocking
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def get_results(self, name: str, artists: List[str], **kwargs) -> Dict[str, str]:
        # Bypassed: We are guessing the URL directly instead of searching.
        return {}

    def extract_lyrics(self, url: str, **_) -> Optional[str]:
        """
        Extracts the lyrics from the given url using BeautifulSoup.
        """
        try:
            response = self.session.get(url, proxies=GlobalConfig.get_parameter("proxies"))
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            lyrics_root = soup.find('div', class_=re.compile(r'^Lyrics__Root'))
            search_area = lyrics_root if lyrics_root else soup

            metadata_classes = ['LyricsHeader', 'SongBio', 'ContributorsCredit', 'ShareButtons', 'SuggestedSongs']
            for metadata_div in search_area.find_all('div', class_=re.compile('|'.join(metadata_classes))):
                metadata_div.decompose()

            for script_or_style in search_area(["script", "style"]):
                script_or_style.decompose()

            lyric_elements = search_area.find_all('div', attrs={"data-lyrics-container": "true"})

            if not lyric_elements:
                return None

            for br in search_area.find_all("br"):
                br.replace_with("\n")

            full_text = "\n\n".join([el.get_text(separator="") for el in lyric_elements])

            # Final Cleanup Process
            clean_text = re.sub(r'\d*Embed$', '', full_text, flags=re.MULTILINE)
            clean_text = re.sub(r'Share$', '', clean_text, flags=re.MULTILINE)
            clean_text = re.sub(r'^.*?Lyrics\n', '', clean_text)
            clean_text = re.sub(r'\n*(\[.*?\])\n*', r'\n\n\1\n', clean_text)
            clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)

            return clean_text.strip()
        except Exception:
            return None

    def get_lyrics(self, name: str, artists: List[str], **kwargs) -> Optional[str]:
        """
        Attempts to guess the Genius URL and scrape it.
        """
        # 1. Manual Override: Check if a custom URL was provided via terminal
        manual_url = os.environ.get("SPOTDL_GENIUS_URL")
        if manual_url:
            lyrics = self.extract_lyrics(manual_url)
            if lyrics:
                return lyrics

        # 2. Automatic Generation: Format Firstname-lastname-song-title-lyrics
        # Clean special characters and format spaces
        clean_artist = re.sub(r'[^a-zA-Z0-9\s-]', '', artists[0]).strip().replace(" ", "-")
        clean_name = re.sub(r'[^a-zA-Z0-9\s-]', '', name).strip().replace(" ", "-")

        # Strip out duplicate dashes
        clean_artist = re.sub(r'-+', '-', clean_artist)
        clean_name = re.sub(r'-+', '-', clean_name)

        # Genius usually capitalizes the first letter of the artist block
        guessed_url = f"https://genius.com/{clean_artist.capitalize()}-{clean_name.lower()}-lyrics"

        lyrics = self.extract_lyrics(guessed_url)
        return lyrics

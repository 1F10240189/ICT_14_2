import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import config
import urllib.parse
from bs4 import BeautifulSoup
import musicbrainzngs # Add this import

class UnifiedMusicService:
    def __init__(self):
        # Spotify APIの認証情報
        client_id = config.SPOTIPY_CLIENT_ID
        client_secret = config.SPOTIPY_CLIENT_SECRET
        self.genius_api_token = config.GENIUS_API_TOKEN

        if not client_id or not client_secret:
            print("エラー: Spotify APIの認証情報が設定されていません。環境変数 SPOTIPY_CLIENT_ID と SPOTIPY_CLIENT_SECRET を設定してください。")
            self.sp = None
        else:
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
        
        if not self.genius_api_token:
            print("エラー: Genius APIの認証情報が設定されていません。環境変数 GENIUS_API_TOKEN を設定してください。")

        # Initialize MusicBrainz client
        musicbrainzngs.set_useragent(
            "ICT_14_2_Music_Recommender",
            "0.1",
            "your_email@example.com" # Replace with a real email
        )
        self.musicbrainz_client = musicbrainzngs # Assign the module itself or a wrapper if needed

    def _get_lyrics_from_genius(self, artist: str, title: str) -> str | None:
        """
        Genius APIを使用して歌詞を取得する
        """
        if not self.genius_api_token:
            return None

        search_url = "https://api.genius.com/search"
        headers = {"Authorization": f"Bearer {self.genius_api_token}"}
        params = {"q": f"{title} {artist}"}

        try:
            response = requests.get(search_url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            hits = data.get("response", {}).get("hits", [])
            if not hits:
                return None

            # Geniusの歌詞ページURLを取得
            lyrics_page_url = hits[0]["result"]["url"]
            
            # 歌詞ページをスクレイピング
            page = requests.get(lyrics_page_url, timeout=10)
            page.raise_for_status()
            soup = BeautifulSoup(page.text, "html.parser")
            lyrics = [div.get_text(separator="\n") for div in soup.select('[data-lyrics-container="true"]')]
            
            return "\n".join(lyrics)
        except requests.exceptions.RequestException as e:
            print(f"Genius APIリクエストに失敗しました: {e}")
            return None

    def search_track_by_name(self, query, limit=5):
        if not self.sp:
            return []
        try:
            results = self.sp.search(q=query, type='track', limit=limit)
            tracks = []
            for item in results['tracks']['items']:
                track_id = item['id']
                track_name = item['name']
                artist_name = item['artists'][0]['name'] if item['artists'] else 'Unknown Artist'
                album_art = item['album']['images'][0]['url'] if item['album']['images'] else None
                preview_url = item['preview_url']
                
                tracks.append({
                    "id": track_id,
                    "name": track_name,
                    "artist": artist_name,
                    "album_art": album_art,
                    "preview_url": preview_url
                })
            return tracks
        except Exception as e:
            print(f"Spotify search_track_by_name failed: {e}")
            return []

    def get_track_info(self, track_id=None, track_name=None, artist_name=None):
        if not track_id and (not track_name or not artist_name):
            print("エラー: track_id または track_name と artist_name の組み合わせが必要です。")
            return {}

        if not track_id:
            # track_id が提供されていない場合、track_name と artist_name で検索
            search_query = f"{track_name} {artist_name}"
            search_results = self.search_track_by_name(search_query, limit=1)
            if search_results:
                track_id = search_results[0]["id"]
            else:
                print(f"Spotifyでトラックが見つかりませんでした: {track_name} by {artist_name}")
                return {}
        if not self.sp:
            return {}
        try:
            track = self.sp.track(track_id)
            artist_name = track['artists'][0]['name'] if track['artists'] else 'Unknown Artist'
            lyrics = self._get_lyrics_from_genius(artist_name, track['name'])

            return {
                "id": track['id'],
                "name": track['name'],
                "artist": artist_name,
                "album_art_url": track['album']['images'][0]['url'] if track['album']['images'] else None,
                "preview_url": track['preview_url'],
                "lyrics": lyrics,
                "duration_ms": track['duration_ms'],
                "popularity": track['popularity']
            }
        except Exception as e:
            print(f"Spotify get_track_info failed: {e}")
            return {}

    def search_musicbrainz_recording(self, query: str, limit: int = 20):
        """
        MusicBrainz APIを使用して録音を検索する
        """
        try:
            # MusicBrainzの検索は、search_recordingsを使用
            # queryは、titleとartistを組み合わせたもの
            result = self.musicbrainz_client.search_recordings(query=query, limit=limit)
            return result.get('recording-list', [])
        except musicbrainzngs.WebServiceError as e:
            print(f"MusicBrainz APIリクエストに失敗しました: {e}")
            return []

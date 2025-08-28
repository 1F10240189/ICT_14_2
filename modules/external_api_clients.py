import os
import requests
import time
import config

class APIClient:
    def __init__(self, base_url, api_key_env_var=None, rate_limit_per_second=None):
        self.base_url = base_url
        self.api_key = os.getenv(api_key_env_var) if api_key_env_var else None
        self.rate_limit_per_second = rate_limit_per_second
        self._last_request_time = 0

    def _make_request(self, endpoint, params=None, headers=None):
        if self.rate_limit_per_second:
            time_since_last_request = time.time() - self._last_request_time
            if time_since_last_request < (1 / self.rate_limit_per_second):
                time.sleep((1 / self.rate_limit_per_second) - time_since_last_request)
        
        url = f"{self.base_url}{endpoint}"
        all_params = {}
        if self.api_key:
            all_params['apikey'] = self.api_key # Musixmatch uses 'apikey'
        if params:
            all_params.update(params)

        try:
            response = requests.get(url, params=all_params, headers=headers)
            response.raise_for_status()  # Raise an exception for HTTP errors
            self._last_request_time = time.time()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {e}")
            return None

class MusicBrainzClient(APIClient):
    def __init__(self):
        super().__init__("https://musicbrainz.org/ws/2/", rate_limit_per_second=1) # MusicBrainz has rate limits
        self.headers = {"User-Agent": "GeminiMusicRecommender/1.0 (your_email@example.com)"} # Required by MusicBrainz

    def search_recording(self, query, limit=10):
        # Search for recordings (songs)
        # query can be 'artist:Nirvana AND recording:Smells Like Teen Spirit'
        # or just 'Smells Like Teen Spirit'
        params = {
            "query": query,
            "fmt": "json",
            "limit": limit
        }
        data = self._make_request("recording/", params=params, headers=self.headers)
        if data and 'recordings' in data:
            return data['recordings']
        return []

    def get_artist_info(self, artist_id):
        # Get artist details, including URLs
        params = {"fmt": "json", "inc": "url-rels"}
        data = self._make_request(f"artist/{artist_id}", params=params, headers=self.headers)
        if data:
            return data
        return None

class AcousticBrainzClient(APIClient):
    def __init__(self):
        super().__init__("https://acousticbrainz.org/api/v1/low-level/", rate_limit_per_second=1) # Also has rate limits

    def get_features(self, mbid):
        # Get low-level acoustic features for a MusicBrainz ID
        # Example: https://acousticbrainz.org/api/v1/low-level/a0b0c0d0-e0f0-1020-3040-5060708090a0
        data = self._make_request(mbid)
        if data:
            return data
        return None

class TheAudioDBClient(APIClient):
    def __init__(self):
        # TheAudioDB requires an API key, but they have a '1' for testing/public use
        super().__init__("https://www.theaudiodb.com/api/v1/json/", api_key_env_var="THEAUDIODB_API_KEY")
        if not self.api_key:
            print("WARNING: THEAUDIODB_API_KEY not set. Using '2' as default for testing.")
            self.api_key = "2" # Public API key for testing, changed from '1' to '2'

    def search_track_image(self, artist_name, track_name):
        # Search for track details which might include album art
        # This API is more artist/album centric for images, might need to search album by artist
        # or get album art from track details if available.
        # Let's try searching for album by artist and then getting album art.
        params = {"s": artist_name, "t": track_name}
        data = self._make_request(f"{self.api_key}/searchtrack.php", params=params)
        if data and 'track' in data and data['track']:
            # Assuming the first track result is relevant
            track_info = data['track'][0]
            return track_info.get('strTrackThumb') or track_info.get('strAlbumThumb')
        return None

    def search_album_image(self, artist_name, album_name):
        params = {"s": artist_name, "a": album_name}
        data = self._make_request(f"{self.api_key}/searchalbum.php", params=params)
        if data and 'album' in data and data['album']:
            album_info = data['album'][0]
            return album_info.get('strAlbumThumb')
        return None

class iTunesSearchClient(APIClient):
    def __init__(self):
        super().__init__("https://itunes.apple.com/search")

    def search_song(self, term, limit=10):
        # Search for songs on iTunes
        params = {
            "term": term,
            "entity": "song",
            "limit": limit
        }
        data = self._make_request("", params=params) # Endpoint is empty for search
        if data and 'results' in data:
            return data['results']
        return []

    def get_preview_url(self, track_id):
        # Get preview URL for a specific track ID
        # This is usually available directly in the search results, but can be fetched if needed.
        # For simplicity, we'll assume it's in the search results.
        pass # Not implementing a separate call for this, as it's in search results.

import urllib.parse # Import for URL encoding

class UnifiedMusicService:
    def __init__(self):
        self.musicbrainz_client = MusicBrainzClient()
        self.acousticbrainz_client = AcousticBrainzClient()
        self.theaudiodb_client = TheAudioDBClient()
        self.itunes_client = iTunesSearchClient()
        # MusixmatchClient removed

    def _get_lyrics_from_lyrics_ovh(self, artist: str, title: str) -> str | None:
        """
        Lyrics.ovh API を使用して歌詞を取得する
        """
        artist_encoded = urllib.parse.quote(artist)
        title_encoded = urllib.parse.quote(title)
        url = f"https://api.lyrics.ovh/v1/{artist_encoded}/{title_encoded}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status() # HTTPエラーがあれば例外を発生
            data = response.json()
            if 'lyrics' in data:
                return data['lyrics']
            else:
                return None # Lyrics not found
        except requests.exceptions.RequestException as e:
            print(f"Lyrics.ovh API request failed: {e}")
            return None

    def search_track_by_name(self, query, limit=5):
        results = []
        # 1. Search MusicBrainz for recordings
        mb_recordings = self.musicbrainz_client.search_recording(query, limit=limit)

        for recording in mb_recordings:
            track_name = recording.get('title')
            artist_name = recording.get('artist-credit')[0].get('name') if recording.get('artist-credit') else 'Unknown Artist'
            mb_recording_id = recording.get('id')
            
            album_art = None
            # Try to get album art from TheAudioDB
            if recording.get('releases'):
                album_name = recording['releases'][0].get('title')
                album_art = self.theaudiodb_client.search_album_image(artist_name, album_name)
            
            # Fallback to iTunes for album art if not found via TheAudioDB
            if not album_art:
                itunes_results = self.itunes_client.search_song(f"{track_name} {artist_name}", limit=1)
                if itunes_results:
                    album_art = itunes_results[0].get('artworkUrl100') # 100x100 artwork

            results.append({
                "id": mb_recording_id,
                "name": track_name,
                "artist": artist_name,
                "album_art": album_art
            })
        return results

    def get_track_info(self, mb_recording_id=None, track_name=None, artist_name=None, album_art_url=None):
        track_info = {
            "mb_recording_id": mb_recording_id,
            "track_name": track_name,
            "artist_name": artist_name,
            "lyrics": None,
            "audio_features": {},
            "preview_url": None,
            "artist_official_url": None, # Renamed from artist_homepage
            "album_art_url": album_art_url # Added album_art_url
        }

        # Get AcousticBrainz features
        if mb_recording_id:
            audio_features = self.acousticbrainz_client.get_features(mb_recording_id)
            if audio_features:
                track_info["audio_features"] = audio_features.get('lowlevel', {}) # Or other relevant sections

        # Get lyrics from Lyrics.ovh
        if track_name and artist_name:
            lyrics = self._get_lyrics_from_lyrics_ovh(artist_name, track_name)
            if lyrics:
                track_info["lyrics"] = lyrics

        # Get preview URL from iTunes
        if track_name and artist_name:
            itunes_results = self.itunes_client.search_song(f"{track_name} {artist_name}", limit=1)
            if itunes_results:
                track_info["preview_url"] = itunes_results[0].get('previewUrl')
                # If album_art_url was not provided, try to get it from iTunes search results
                if not track_info["album_art_url"]:
                    track_info["album_art_url"] = itunes_results[0].get('artworkUrl100')

        # Get artist homepage from MusicBrainz
        if mb_recording_id: # Need to get artist ID from recording first
            mb_recordings = self.musicbrainz_client.search_recording(f"rid:{mb_recording_id}", limit=1)
            if mb_recordings:
                artist_id = mb_recordings[0].get('artist-credit')[0].get('artist', {}).get('id')
                if artist_id:
                    artist_info = self.musicbrainz_client.get_artist_info(artist_id)
                    if artist_info and 'url-rels' in artist_info:
                        official_url = next((rel['target'] for rel in artist_info['url'] if rel['type'] == 'official homepage'), None) # Changed from url-rels to url
                        track_info["artist_official_url"] = official_url
        
        return track_info

# Example Usage (for testing purposes, not part of the main flow)
if __name__ == "__main__":
    # Ensure API keys are set in your environment variables for TheAudioDB
    # export THEAUDIODB_API_KEY='YOUR_API_KEY' (or use '2' for testing)

    print("--- Testing MusicBrainzClient ---")
    mb_client = MusicBrainzClient()
    recordings = mb_client.search_recording("artist:Nirvana AND recording:Smells Like Teen Spirit")
    if recordings:
        print(f"Found {len(recordings)} recordings for 'Smells Like Teen Spirit' by Nirvana.")
        first_recording = recordings[0]
        print(f"First recording: {first_recording.get('title')} by {first_recording.get('artist-credit')[0].get('name')}")
        
        artist_id = first_recording.get('artist-credit')[0].get('artist', {}).get('id')
        if artist_id:
            artist_info = mb_client.get_artist_info(artist_id)
            if artist_info and 'url-rels' in artist_info:
                official_url = next((rel['target'] for rel in artist_info['url-rels'] if rel['type'] == 'official homepage'), None)
                print(f"Nirvana Official Homepage: {official_url}")

    print("\n--- Testing AcousticBrainzClient ---")
    # You need a valid MusicBrainz ID for this. Let's use a known one for testing.
    # Example MBID for 'Smells Like Teen Spirit' recording: 2b070900-2203-4120-927f-122220000000
    # (This is a placeholder, you'd get it from MusicBrainz search)
    test_mbid = "2b070900-2203-4120-927f-122220000000" # Replace with a real MBID if testing
    acoustic_features = AcousticBrainzClient().get_features(test_mbid)
    if acoustic_features:
        print(f"Acoustic features for {test_mbid}: {acoustic_features.get('metadata', {}).get('tags', {}).get('genre', 'N/A')}")
    else:
        print(f"Could not retrieve AcousticBrainz features for {test_mbid}. (Might be a placeholder MBID or no data)")

    print("\n--- Testing TheAudioDBClient ---")
    audio_db_client = TheAudioDBClient()
    album_thumb = audio_db_client.search_album_image("Nirvana", "Nevermind")
    if album_thumb:
        print(f"Nevermind Album Thumb: {album_thumb}")
    else:
        print("Could not find album thumb for Nevermind.")

    print("\n--- Testing iTunesSearchClient ---")
    itunes_client = iTunesSearchClient()
    itunes_results = itunes_client.search_song("Smells Like Teen Spirit Nirvana", limit=1)
    if itunes_results:
        first_result = itunes_results[0]
        print(f"iTunes Result: {first_result.get('trackName')} by {first_result.get('artistName')}")
        print(f"Preview URL: {first_result.get('previewUrl')}")
    else:
        print("No iTunes results found.")

    print("\n--- Testing UnifiedMusicService ---")
    unified_service = UnifiedMusicService()
    search_results = unified_service.search_track_by_name("Smells Like Teen Spirit Nirvana", limit=1)
    if search_results:
        print(f"Unified Search Result: {search_results[0].get('name')} by {search_results[0].get('artist')}")
        print(f"Album Art: {search_results[0].get('album_art')}")
        
        track_details = unified_service.get_track_info(
            mb_recording_id=search_results[0]['id'],
            track_name=search_results[0]['name'],
            artist_name=search_results[0]['artist'],
            album_art_url=search_results[0].get('album_art') # Pass album_art_url from search results
        )
        print(f"Track Details: {track_details.get('track_name')}")
        print(f"Preview URL: {track_details.get('preview_url')}")
        print(f"Artist Official URL: {track_details.get('artist_official_url')}") # Renamed
        print(f"Album Art URL: {track_details.get('album_art_url')}") # Added
        print(f"Lyrics (first 100 chars): {track_details.get('lyrics', '')[:100]}...")
        print(f"Audio Features keys: {track_details.get('audio_features', {}).keys()}")
    else:
        print("No unified search results found.")

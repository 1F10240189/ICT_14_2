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
            all_params['api_key'] = self.api_key # Assuming 'api_key' as param name
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
            print("WARNING: THEAUDIODB_API_KEY not set. Using '1' as default for testing.")
            self.api_key = "1" # Public API key for testing

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

# Example Usage (for testing purposes, not part of the main flow)
if __name__ == "__main__":
    # Ensure API keys are set in your environment variables for TheAudioDB
    # export THEAUDIODB_API_KEY='YOUR_API_KEY' (or use '1' for testing)

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
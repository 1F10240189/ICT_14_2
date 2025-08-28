import os
import requests
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import config
import urllib.parse

class UnifiedMusicService:
    def __init__(self):
        # Spotify APIの認証情報
        client_id = config.SPOTIPY_CLIENT_ID
        client_secret = config.SPOTIPY_CLIENT_SECRET

        if not client_id or not client_secret:
            print("エラー: Spotify APIの認証情報が設定されていません。環境変数 SPOTIPY_CLIENT_ID と SPOTIPY_CLIENT_SECRET を設定してください。")
            # アプリケーションの起動を停止するか、テスト用のダミーデータを使用するなどの対応が必要
            # 今回はエラーメッセージを出力して続行するが、本番環境では適切なエラーハンドリングが必要
            self.sp = None
        else:
            self.sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret))
        
        # Lyrics.ovh の利用は継続

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

    def get_track_info(self, track_id):
        if not self.sp:
            return {}
        try:
            track = self.sp.track(track_id)
            artist_name = track['artists'][0]['name'] if track['artists'] else 'Unknown Artist'
            lyrics = self._get_lyrics_from_lyrics_ovh(artist_name, track['name'])

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

    def get_artist_info(self, artist_id):
        if not self.sp:
            return {}
        try:
            artist = self.sp.artist(artist_id)
            return {
                "id": artist['id'],
                "name": artist['name'],
                "genres": artist['genres'],
                "followers": artist['followers']['total'],
                "images": artist['images']
            }
        except Exception as e:
            print(f"Spotify get_artist_info failed: {e}")
            return {}

    def get_related_artists(self, artist_id):
        if not self.sp:
            return []
        try:
            results = self.sp.artist_related_artists(artist_id)
            related_artists = []
            for artist in results['artists']:
                related_artists.append({
                    "id": artist['id'],
                    "name": artist['name'],
                    "genres": artist['genres'],
                    "images": artist['images']
                })
            return related_artists
        except Exception as e:
            print(f"Spotify get_related_artists failed: {e}")
            return []

    def get_recommendations(self, seed_tracks=None, seed_artists=None, seed_genres=None, limit=5):
        if not self.sp:
            return []
        try:
            results = self.sp.recommendations(
                seed_tracks=seed_tracks,
                seed_artists=seed_artists,
                seed_genres=seed_genres,
                limit=limit
            )
            recommended_tracks = []
            for track in results['tracks']:
                recommended_tracks.append({
                    "id": track['id'],
                    "name": track['name'],
                    "artist": track['artists'][0]['name'] if track['artists'] else 'Unknown Artist',
                    "album_art": track['album']['images'][0]['url'] if track['album']['images'] else None,
                    "preview_url": track['preview_url']
                })
            return recommended_tracks
        except Exception as e:
            print(f"Spotify get_recommendations failed: {e}")
            return []

    def get_audio_features(self, track_ids):
        if not self.sp:
            return []
        try:
            features = self.sp.audio_features(track_ids)
            return features
        except Exception as e:
            print(f"Spotify get_audio_features failed: {e}")
            return []

    def get_audio_analysis(self, track_id):
        if not self.sp:
            return {}
        try:
            analysis = self.sp.audio_analysis(track_id)
            return analysis
        except Exception as e:
            print(f"Spotify get_audio_analysis failed: {e}")
            return {}

    def get_featured_playlists(self, limit=5):
        if not self.sp:
            return []
        try:
            playlists = self.sp.featured_playlists(limit=limit)
            featured_list = []
            for item in playlists['playlists']['items']:
                featured_list.append({
                    "id": item['id'],
                    "name": item['name'],
                    "description": item['description'],
                    "images": item['images'],
                    "external_urls": item['external_urls']['spotify']
                })
            return featured_list
        except Exception as e:
            print(f"Spotify get_featured_playlists failed: {e}")
            return []

    def get_category_playlists(self, category_id, limit=5):
        if not self.sp:
            return []
        try:
            playlists = self.sp.category_playlists(category_id, limit=limit)
            category_list = []
            for item in playlists['playlists']['items']:
                category_list.append({
                    "id": item['id'],
                    "name": item['name'],
                    "description": item['description'],
                    "images": item['images'],
                    "external_urls": item['external_urls']['spotify']
                })
            return category_list
        except Exception as e:
            print(f"Spotify get_category_playlists failed: {e}")
            return []

# Example Usage (for testing purposes, not part of the main flow)
if __name__ == "__main__":
    # 環境変数に SPOTIPY_CLIENT_ID と SPOTIPY_CLIENT_SECRET を設定してください
    # export SPOTIPY_CLIENT_ID='YOUR_CLIENT_ID'
    # export SPOTIPY_CLIENT_SECRET='YOUR_CLIENT_SECRET'

    print("--- Testing UnifiedMusicService with Spotify API ---")
    unified_service = UnifiedMusicService()

    if unified_service.sp:
        # Search Track
        print("\n--- Searching for 'Smells Like Teen Spirit' ---")
        search_results = unified_service.search_track_by_name("Smells Like Teen Spirit Nirvana", limit=1)
        if search_results:
            track = search_results[0]
            print(f"Found Track: {track['name']} by {track['artist']}")
            print(f"Album Art: {track['album_art']}")
            print(f"Preview URL: {track['preview_url']}")

            # Get Track Info
            print("\n--- Getting Track Info ---")
            track_info = unified_service.get_track_info(track['id'])
            if track_info:
                print(f"Track Name: {track_info['name']}")
                print(f"Lyrics (first 100 chars): {track_info['lyrics'][:100]}...")
                print(f"Duration (ms): {track_info['duration_ms']}")
                print(f"Popularity: {track_info['popularity']}")

            # Get Artist Info
            print("\n--- Getting Artist Info (Nirvana) ---")
            # First, find Nirvana's artist ID from the track
            artist_id = unified_service.sp.track(track['id'])['artists'][0]['id']
            artist_info = unified_service.get_artist_info(artist_id)
            if artist_info:
                print(f"Artist Name: {artist_info['name']}")
                print(f"Genres: {artist_info['genres']}")
                print(f"Followers: {artist_info['followers']}")

            # Get Related Artists
            print("\n--- Getting Related Artists for Nirvana ---")
            related_artists = unified_service.get_related_artists(artist_id)
            if related_artists:
                for i, artist in enumerate(related_artists[:3]):
                    print(f"  {i+1}. {artist['name']}")

            # Get Recommendations (using the found track as a seed)
            print("\n--- Getting Recommendations ---")
            recommendations = unified_service.get_recommendations(seed_tracks=[track['id']], limit=3)
            if recommendations:
                for i, rec_track in enumerate(recommendations):
                    print(f"  {i+1}. {rec_track['name']} by {rec_track['artist']}")

            # Get Audio Features
            print("\n--- Getting Audio Features ---")
            audio_features = unified_service.get_audio_features([track['id']])
            if audio_features:
                print(f"  Danceability: {audio_features[0]['danceability']}")
                print(f"  Energy: {audio_features[0]['energy']}")

            # Get Audio Analysis
            print("\n--- Getting Audio Analysis ---")
            audio_analysis = unified_service.get_audio_analysis(track['id'])
            if audio_analysis:
                print(f"  Tempo: {audio_analysis['track']['tempo']}")
                print(f"  Key: {audio_analysis['track']['key']}")

            # Get Featured Playlists
            print("\n--- Getting Featured Playlists ---")
            featured_playlists = unified_service.get_featured_playlists(limit=2)
            if featured_playlists:
                for i, playlist in enumerate(featured_playlists):
                    print(f"  {i+1}. {playlist['name']} - {playlist['description'][:50]}...")

            # Get Category Playlists (e.g., 'rock')
            print("\n--- Getting 'Rock' Category Playlists ---")
            # You might need to get category IDs first using sp.categories()
            # For now, let's assume 'rock' category ID is known or find one dynamically
            # Example: sp.categories() to get available categories and their IDs
            try:
                categories = unified_service.sp.categories(limit=1) # Just to get one category ID for testing
                if categories and categories['categories']['items']:
                    test_category_id = categories['categories']['items'][0]['id']
                    print(f"Using test category ID: {test_category_id}")
                    category_playlists = unified_service.get_category_playlists(test_category_id, limit=2)
                    if category_playlists:
                        for i, playlist in enumerate(category_playlists):
                            print(f"  {i+1}. {playlist['name']} - {playlist['description'][:50]}...")
            except Exception as e:
                print(f"Could not get category playlists for testing: {e}")

    else:
        print("Spotify APIクライアントが初期化されませんでした。テストをスキップします。")
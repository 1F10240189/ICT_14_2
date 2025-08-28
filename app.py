from dotenv import load_dotenv
load_dotenv()

import gradio as gr
import json
from modules.recommender import LyricRecommender
from modules.external_api_clients import UnifiedMusicService

# --- データ読み込み ---
def load_song_data(path="data/songs.json"):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            songs_list = json.load(f)
        songs_dict = {song['track']: {"artist": song['artist'], "lyrics": song['lyrics']} for song in songs_list}
        song_titles = [song['track'] for song in songs_list]
        print(f"✅ {len(song_titles)}件の楽曲データを {path} から読み込みました。")
        return songs_dict, song_titles
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error: {path} の読み込みに失敗しました。({e})")
        exit()

# --- 初期化 ---
songs_db, song_titles_for_examples = load_song_data()
recommender = LyricRecommender()
music_service = UnifiedMusicService()
print("✅ Recommender engine and Music Service loaded.")

# --- 推薦処理 ---
def recommend_song(track_id, track_name, artist_name, album_art_url):
    if not track_id:
        return "曲が選択されていません。検索して選択してください。"

    song_details = music_service.get_track_info(track_id)
    lyrics = song_details.get("lyrics", "")

    if not lyrics:
        return f"申し訳ありません。「{track_name}」の歌詞が見つかりませんでした。"

    recommendation = recommender.recommend(
        selected_mb_recording_id=track_id,
        selected_song_title=track_name,
        selected_artist_name=artist_name,
        selected_song_lyrics=lyrics,
        selected_album_art_url=album_art_url
    )
    return recommendation

# --- 検索処理 ---
def search_tracks(query):
    if not query or len(query) < 2:
        return [], []

    results = music_service.search_track_by_name(query, limit=5)
    if not results:
        return [], []

    gallery_items = [
        (t.get("album_art") or "https://via.placeholder.com/150", f"{t['name']} - {t['artist']}")
        for t in results
    ]

    value_list = [
        {"id": t["id"], "name": t["name"], "artist": t["artist"], "album_art": t.get("album_art") or ""}
        for t in results
    ]

    return gallery_items, value_list

# --- ギャラリー選択 ---
def on_select(evt: gr.SelectData, value_list):
    idx = evt.index
    track = value_list[idx]
    return track["id"], track["name"], track["artist"], track["album_art"], f"{track['name']} - {track['artist']}"

# --- UI ---
def create_ui():
    with gr.Blocks(title="AI Lyric Recommender 🎵") as demo:
        gr.Markdown("# AI Lyric Recommender 🎵")
        gr.Markdown("曲名またはアーティスト名で検索して、アルバム画像をクリックしてください。")

        with gr.Row():
            with gr.Column(scale=2):
                track_search_input = gr.Textbox(
                    label="曲名またはアーティスト名で検索",
                    placeholder="例: Smells Like Teen Spirit Nirvana"
                )
                search_results = gr.Gallery(label="検索結果", elem_id="search_gallery")

                hidden_values = gr.State([])

                selected_track_id = gr.Textbox(visible=False)
                selected_track_name = gr.Textbox(visible=False)
                selected_artist_name = gr.Textbox(visible=False)
                selected_album_art_url = gr.Textbox(visible=False)
                selected_track_display_output = gr.Textbox(label="選択中の曲", interactive=False)

                submit_button = gr.Button("この曲で推薦してもらう")

            with gr.Column(scale=3):
                recommendation_output = gr.Markdown(label="推薦結果")

        # 検索イベント
        track_search_input.change(
            fn=search_tracks,
            inputs=track_search_input,
            outputs=[search_results, hidden_values]
        )

        # ギャラリー選択イベント
        search_results.select(
            fn=on_select,
            inputs=hidden_values,
            outputs=[selected_track_id, selected_track_name, selected_artist_name, selected_album_art_url, selected_track_display_output]
        )

        # 推薦イベント
        submit_button.click(
            fn=recommend_song,
            inputs=[selected_track_id, selected_track_name, selected_artist_name, selected_album_art_url],
            outputs=recommendation_output
        )

    return demo

# --- アプリ起動 ---
if __name__ == "__main__":
    demo = create_ui()
    demo.launch(share=True)

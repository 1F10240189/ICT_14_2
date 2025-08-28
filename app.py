from dotenv import load_dotenv
load_dotenv()

import gradio as gr
import json
from modules.recommender import LyricRecommender
from modules.external_api_clients import UnifiedMusicService

# --- データの読み込み ---
# アプリケーション起動時に一度だけsongs.jsonを読み込みます。
def load_song_data(path="data/songs.json"):
    """
    JSONファイルから楽曲データを読み込み、
    UIテスト用の辞書と曲名リストを作成する関数
    """
    try:
        with open(path, 'r', encoding='utf-8') as f:
            songs_list = json.load(f)
        
        # 扱いやすいように曲名をキーにした辞書に変換
        songs_dict = {song['track']: {"artist": song['artist'], "lyrics": song['lyrics']} for song in songs_list}
        song_titles = [song['track'] for song in songs_list]
        
        print(f"✅ {len(song_titles)}件の楽曲データを data/songs.json から読み込みました。")
        return songs_dict, song_titles
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"❌ Error: {path} の読み込みに失敗しました。({e})")
        print("アプリケーションを終了します。data/songs.jsonファイルを確認してください。")
        exit() # データがなければアプリを起動しても意味がないので終了

# --- アプリケーションの初期化 ---
# JSONから楽曲データを読み込む
songs_db, song_titles_for_examples = load_song_data()

# 推薦エンジンと外部音楽サービスを初期化
recommender = LyricRecommender()
music_service = UnifiedMusicService()
print("✅ Recommender engine and Music Service loaded.")

# --- Gradioの応答関数 ---
def recommend_song(selected_track_id, selected_track_name, selected_artist_name, selected_album_art_url):
    """
    ユーザーが選択した曲のIDを受け取り、推薦結果を返す関数
    """
    if not selected_track_id:
        return "曲が選択されていません。検索して選択してください。"

    # 選択された曲の詳細情報を外部APIから取得
    # ここでは、ローカルDBの歌詞を優先しつつ、外部APIから音響特徴量などを取得する
    selected_song_lyrics = ""
    local_song_info = songs_db.get(selected_track_name) # ローカルDBから歌詞を取得
    if local_song_info:
        selected_song_lyrics = local_song_info["lyrics"]

    # 外部APIから詳細情報を取得 (MusicBrainz ID, 歌詞、音響特徴量など)
    # get_track_infoはMusicBrainz IDを期待する
    selected_song_details = music_service.get_track_info(
        mb_recording_id=selected_track_id,
        track_name=selected_track_name,
        artist_name=selected_artist_name,
        album_art_url=selected_album_art_url # Pass album_art_url
    )
    
    # 外部APIから歌詞が取得できた場合はそちらを優先
    if selected_song_details.get("lyrics"): 
        selected_song_lyrics = selected_song_details["lyrics"]

    if not selected_song_lyrics:
        return f"申し訳ありません。「{selected_track_name}」の歌詞が見つかりませんでした。"

    print(f"ユーザーが選択した曲: {selected_track_name} (ID: {selected_track_id})")

    # --- 推薦処理 ---
    recommendation_text = recommender.recommend(
        selected_mb_recording_id=selected_track_id,
        selected_song_title=selected_track_name,
        selected_artist_name=selected_artist_name,
        selected_song_lyrics=selected_song_lyrics,
        selected_album_art_url=selected_album_art_url # Pass album_art_url
    )
    
    return recommendation_text


def search_tracks(query):
    """
    検索クエリに基づいて楽曲を検索し、結果をHTML形式で返す関数
    """
    if not query or len(query) < 2:
        return ""

    results = music_service.search_track_by_name(query, limit=5)
    
    if not results:
        return "<div class='no-results'>曲が見つかりませんでした。</div>"

    html_output = ""
    for track in results:
        # MusicBrainz IDをdata属性として埋め込む
        html_output += f"""
        <div class='search-result-item' 
             data-track-id='{track.get('id')}' 
             data-track-name='{track.get('name')}' 
             data-artist-name='{track.get('artist')}' 
             data-album-art='{track.get('album_art') or ''}'>
            <img src="{track.get('album_art') or 'https://via.placeholder.com/64'}" alt="{track.get('name')}" class="album-art">
            <div class="track-info">
                <span class="track-name">{track.get('name')}</span>
                <span class="artist-name">{track.get('artist')}</span>
            </div>
        </div>
        """
    
    # Embed JavaScript directly into the HTML output
    html_output += """
    <script>
        alert("Script is running!"); // Added for debugging
        // This script will execute when the HTML is rendered.
        // It attaches click listeners to the search result items.
        const items = document.querySelectorAll('.search-result-item');
        items.forEach(item => {
            item.onclick = () => {
                const trackId = item.dataset.trackId;
                const trackName = item.dataset.trackName;
                const artistName = item.dataset.artistName;
                const albumArt = item.dataset.albumArt;
                
                // 隠しコンポーネントの値を更新
                const selectedTrackIdComp = document.querySelector('#selected_track_id_comp');
                const selectedTrackNameComp = document.querySelector('#selected_track_name_comp');
                const selectedArtistNameComp = document.querySelector('#selected_artist_name_comp');
                const selectedAlbumArtUrlComp = document.querySelector('#selected_album_art_url_comp');
                const selectedTrackDisplayOutputComp = document.querySelector('#selected_track_display_output_comp');

                if (selectedTrackIdComp) selectedTrackIdComp.value = trackId;
                if (selectedTrackNameComp) selectedTrackNameComp.value = trackName;
                if (selectedArtistNameComp) selectedArtistNameComp.value = artistName;
                if (selectedAlbumArtUrlComp) selectedAlbumArtUrlComp.value = albumArt;
                if (selectedTrackDisplayOutputComp) selectedTrackDisplayOutputComp.value = `${trackName} - ${artistName}`;

                // 検索結果をクリア
                const searchResultsHtml = document.querySelector('div[data-testid="html"]');
                if (searchResultsHtml) searchResultsHtml.innerHTML = '';

                // 推薦ボタンを有効化 (必要であれば)
                // const submitButton = document.querySelector('button[data-testid="submit-button"]');
                // if (submitButton) submitButton.disabled = false;
            };
        });
    </script>
    """

    return html_output

# --- Gradio UIの構築 ---
def create_ui():
    with gr.Blocks(title="AI Lyric Recommender 🎵") as demo:
        gr.Markdown("# AI Lyric Recommender 🎵")
        gr.Markdown("好きな曲を検索して選択すると、歌詞や雰囲気、音響的特徴が似ている曲をAIが推薦します。")

        with gr.Row():
            with gr.Column(scale=2):
                track_search_input = gr.Textbox(
                    label="曲名またはアーティスト名で検索",
                    placeholder="例: Smells Like Teen Spirit Nirvana",
                    interactive=True
                )
                search_results_html = gr.HTML(label="検索結果")
                
                # 選択された曲の情報を保持する隠しコンポーネント
                selected_track_id = gr.Textbox(visible=False, elem_id="selected_track_id_comp")
                selected_track_name = gr.Textbox(visible=False, elem_id="selected_track_name_comp")
                selected_artist_name = gr.Textbox(visible=False, elem_id="selected_artist_name_comp")
                selected_album_art_url = gr.Textbox(visible=False, elem_id="selected_album_art_url_comp") # New hidden component

                # 新しい表示用コンポーネント
                selected_track_display_output = gr.Textbox(
                    label="選択中の曲",
                    interactive=False,
                    elem_id="selected_track_display_output_comp"
                )

                submit_button = gr.Button("この曲で推薦してもらう")

            with gr.Column(scale=3):
                recommendation_output = gr.Markdown(label="推薦結果")

        # 検索入力の変更時に検索を実行
        track_search_input.change(
            fn=search_tracks,
            inputs=track_search_input,
            outputs=search_results_html,
            queue=False
        )

        # 推薦ボタンのクリック時に推薦を実行
        submit_button.click(
            fn=recommend_song,
            inputs=[selected_track_id, selected_track_name, selected_artist_name, selected_album_art_url],
            outputs=recommendation_output
        )

    return demo

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    demo = create_ui()
    demo.launch(share=True)
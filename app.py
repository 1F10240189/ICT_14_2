# app.py
import gradio as gr
import json
# from modules.recommender import LyricRecommender # バックエンド完成後にコメントを外します

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

# 他の人が作成する推薦エンジン。準備ができたら下のコメントアウトを外す
# recommender = LyricRecommender()
# print("✅ Recommender engine loaded.")


# --- Gradioの応答関数 ---
def respond(message, history):
    """
    ユーザーからのメッセージ(曲名)を受け取り、推薦結果を返す関数
    """
    selected_title = (message or "").strip()
    if not selected_title:
        return "曲名を入力してください。"

    # --- UIテスト用のデータ検索 (読み込んだデータから) ---
    selected_song = songs_db.get(selected_title)
    if not selected_song:
        return f"申し訳ありません。「{selected_title}」という曲はデータベースにありません。"
    
    print(f"ユーザーが選択した曲: {selected_title}")

    # --- (仮の)推薦処理 ---
    # バックエンド担当者のrecommender.pyが完成したら、下のコメントアウトを外して差し替えます。
    # recommendation_text = recommender.recommend(
    #     selected_song_title=selected_title,
    #     selected_song_lyrics=selected_song["lyrics"]
    # )
    
    # UI開発用の仮の返信メッセージ
    recommendation_text = f"「{selected_title}」ですね！\n\n"
    recommendation_text += "現在、AIがあなたへのおすすめを選んでいます...\n"
    recommendation_text += "（これはUI開発用のメッセージです。バックエンド接続後に、ここに推薦文が表示されます。）"
    
    return recommendation_text


# --- Gradio UIの構築 ---
def create_ui():
    """GradioのChatInterfaceを作成して返す"""
    return gr.ChatInterface(
        fn=respond,
        title="AI Lyric Recommender 🎵",
        description="好きな曲を選ぶと、歌詞の雰囲気が似ている曲をAIが推薦します。",
        examples=song_titles_for_examples, # 起動時に読み込んだ曲名リストを使用
        submit_btn="この曲で推薦してもらう",
        stop_btn="停止"
    )

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    demo = create_ui()
    # share=Trueにすると、外部からアクセスできるURLが生成されます
    demo.launch(share=True)
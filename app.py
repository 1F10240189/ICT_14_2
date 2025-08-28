# app.py (修正版)
import gradio as gr

# 他の担当者が作成するモジュールと仮データをインポート
from modules.recommender import LyricRecommender 
from data.songs_db_mock import songs_db

# --- アプリケーションの初期化 ---
# 推薦エンジンのインスタンスを作成
# (バックエンド担当者がrecommender.pyを完成させたら、この部分はそのまま使えます)
recommender = LyricRecommender()
print("✅ Recommender engine loaded.")


# --- Gradioの応答関数 ---
def respond(message, history):
    """
    ユーザーからのメッセージ(曲名)を受け取り、推薦結果を返す関数
    """
    selected_title = (message or "").strip()
    if not selected_title:
        return "曲名を入力してください。"

    # --- UIテスト用の仮データから曲を検索 ---
    selected_song = songs_db.get(selected_title)
    if not selected_song:
        return f"申し訳ありません。「{selected_title}」という曲はデータベースにありません。"
    
    print(f"ユーザーが選択した曲: {selected_title}")

    # --- 推薦モジュールを呼び出す ---
    # RAG担当者が作成した recommender.recommend を呼び出します
    recommendation_text = recommender.recommend(
        selected_song_title=selected_title,
        selected_song_lyrics=selected_song["lyrics"]
    )
    
    return recommendation_text


# --- Gradio UIの構築 ---
def create_ui():
    """GradioのChatInterfaceを作成して返す"""
    # データベース内の曲名を例文として表示できるようにリスト化
    song_titles = list(songs_db.keys())

    # 講義資料のUI部分を参考にしています
    return gr.ChatInterface(
        fn=respond,
        title="AI Lyric Recommender 🎵",
        description="好きな曲を選ぶと、歌詞の雰囲気が似ている曲をAIが推薦します。",
        examples=song_titles,
        submit_btn="この曲で推薦してもらう",
        stop_btn="停止",
        placeholder="ここに曲名を入力、または下の例文をクリックしてください..."
    )

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    demo = create_ui()
    # share=True にすると、チームメンバーがアクセスできる公開URLが生成されます
    demo.launch(share=True)
# app.py
from flask import Flask
import gradio as gr
from modules.recommender import LyricRecommender # 他の人が作る予定の推薦モジュール
from data.songs_db_mock import songs_db # UIテスト用の仮データベース

# --- アプリケーションの初期化 ---
# 推薦エンジンのインスタンスを作成
# (完成版ができたら、この1行を書き換えるだけでOK)
recommender = LyricRecommender()
print("✅ Recommender engine loaded.")


# --- Gradioの応答関数 ---
# Gradio Interfaceは、この関数を呼び出して応答を生成します。
def respond(message, history):
    """
    ユーザーからのメッセージ(曲名)を受け取り、推薦結果を返す関数
    """
    selected_title = (message or "").strip()
    if not selected_title:
        return "曲名を入力してください。"

    # --- UIテスト用の仮データ検索 ---
    # (本来はrecommenderモジュールがこの役割を担う)
    selected_song = songs_db.get(selected_title)
    if not selected_song:
        return f"申し訳ありません。「{selected_title}」という曲はデータベースにありません。"
    
    print(f"ユーザーが選択した曲: {selected_title}")

    # --- 推薦モジュールを呼び出す ---
    # 他の人が作成したrecommender.recommendを呼び出す
    # 入力: 曲名、歌詞  出力: LLMが生成した推薦文(文字列)
    recommendation_text = recommender.recommend(
        selected_song_title=selected_title,
        selected_song_lyrics=selected_song["lyrics"]
    )
    
    return recommendation_text


# --- Gradio UIの構築 ---
# 添付資料の「2.9. Chatbot（RAG）の起動」セルを参考にしています。
def create_ui():
    """GradioのChatInterfaceを作成して返す"""
    # データベース内の曲名をサジェストできるようにリスト化
    song_titles = list(songs_db.keys())

    return gr.ChatInterface(
        fn=respond,
        title="AI Lyric Recommender 🎵",
        description="好きな曲を選ぶと、歌詞の雰囲気が似ている曲をAIが推薦します。",
        examples=song_titles, # データベース内の曲名を例文として表示
        submit_btn="この曲で推薦してもらう",
        stop_btn="停止",
        placeholder="ここに曲名を入力、または下の例文をクリックしてください..."
    )

# --- アプリケーションの起動 ---
if __name__ == "__main__":
    demo = create_ui()
    # share=Trueにすると、外部からアクセスできるURLが生成されます
    demo.launch(share=True)
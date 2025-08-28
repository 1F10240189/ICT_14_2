# config.py
# # APIキーやモデル名を設定するファイル
import os
os.environ['OPENAI_API_KEY'] = '5qBg0lkoqdMwMseQ4tg-K71jjWXeNdJFiDhR_gDvbWaWzAJYvFJn_Rr-Y3-CsMamBlhaH8TwfzQgFyPsEjlYHWg'


OPENAI_API_BASE="https://api.openai.iniad.org/api/v1"

EMBED_MODEL = "text-embedding-3-small"
LLM_MODEL       = "gpt-4o-mini"

# --- データベース関連 ---
# 楽曲データのJSONファイルへのパス
SONGS_JSON_PATH = "data/songs.json"

# ベクトルデータベース(ChromaDB)の保存先ディレクトリ
CHROMA_DIR = "vectorstore"

# ChromaDBのコレクション名
COLLECTION_NAME = "lyric_vectors"

# 類似度スコアのしきい値 (0.0から1.0の範囲で、高いほど類似度が高い)
SCORE_THRESHOLD = 0.3

# --- 外部API関連 ---
# Spotify API Credentials
SPOTIPY_CLIENT_ID = os.getenv("SPOTIPY_CLIENT_ID", "c0146d0eab3742b7bbf89c09c0e5588e")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "58c0b49dafaf4757bc9145c6105afd00")
# No longer using Musixmatch API KEY
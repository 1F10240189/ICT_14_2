# config.py
# # APIキーやモデル名を設定するファイル
OPENAI_API_BASE = "https://api.openai.com/v1"  # 必要に応じてURLを変更

EMBED_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4-mini"

# APIサーバーのURL (通常は変更不要)
OPENAI_API_BASE = "https://api.openai.com/v1"


# --- データベース関連 ---
# 楽曲データのJSONファイルへのパス
SONGS_JSON_PATH = "data/songs.json"

# ベクトルデータベース(ChromaDB)の保存先ディレクトリ
CHROMA_DIR = "vectorstore"

# ChromaDBのコレクション名
COLLECTION_NAME = "lyric_vectors"
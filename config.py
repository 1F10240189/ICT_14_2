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
# TheAudioDBのAPIキー (テスト用は'1')
# 環境変数で設定することを推奨: export THEAUDIODB_API_KEY='YOUR_KEY'
THEAUDIODB_API_KEY = os.getenv("THEAUDIODB_API_KEY", "1")


# data/songs.jsonからベクトルDBを構築する実行スクリプト
# build_database.py
from modules.data_loader import load_songs_as_documents
from modules.vectorizer import build_and_persist_vector_store
import config

print("--- 歌詞ベクトルデータベースの構築を開始します ---")

# 1. data/songs.json からドキュメントを読み込む
print("[1/2] 楽曲データを読み込んでいます...")
documents = load_songs_as_documents(config.SONGS_JSON_PATH)

# 2. ドキュメントをベクトル化し、ChromaDBに保存する
print(f"[2/2] {len(documents)}件の楽曲をベクトル化し、DBに保存します...")
build_and_persist_vector_store(documents)

print("★★★ データベースの構築が完了しました！ ★★★")
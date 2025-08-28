# data/songs.jsonからベクトルDBを構築する実行スクリプト
# build_database.py
from modules.vectorizer import Vectorizer

print("--- 歌詞ベクトルデータベースの構築を開始します ---")

# Vectorizerクラスのインスタンスを作成し、データベース構築を実行
vectorizer = Vectorizer()
vectorizer.run()

print("★★★ データベースの構築が完了しました！ ★★★")
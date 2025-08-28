# Documentをベクトル化し、ChromaDBに保存するモジュール# modules/vectorizer.py
import os
import json
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain.docstore.document import Document
import config

class Vectorizer:
    def __init__(self):
        """初期化時に、EmbeddingsとChromaDBのクライアントを準備"""
        self.embeddings = OpenAIEmbeddings(
            openai_api_base=config.OPENAI_API_BASE,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model=config.EMBED_MODEL
        )
        # 保存先のディレクトリが存在しない場合は作成
        if not os.path.exists(config.CHROMA_DIR):
            os.makedirs(config.CHROMA_DIR)
            
        self.vectorstore = Chroma(
            collection_name=config.COLLECTION_NAME,
            persist_directory=config.CHROMA_DIR,
            embedding_function=self.embeddings
        )

    def load_songs_from_json(self, file_path="data/songs.json"):
        """
        JSONファイルから曲のデータを読み込む
        """
        print(f"🎵 {file_path} から曲データを読み込んでいます...")
        with open(file_path, 'r', encoding='utf-8') as f:
            # JSONをパースしてdictのリストに変換
            songs = json.load(f)
        print(f"✅ {len(songs)} 曲のデータを読み込みました。")
        return songs

    def create_documents(self, songs_data):
        """
        曲データ(dictのリスト)を、LangChainのDocumentオブジェクトのリストに変換
        """
        print("📜 Documentオブジェクトを作成中...")
        documents = []
        for song in songs_data:
            # Documentオブジェクトを作成
            # page_content: ベクトル化対象のテキスト
            # metadata:     検索時に参照したい情報
            doc = Document(
                page_content=song["lyrics"],
                metadata={"title": song["title"], "artist": song["artist"]}
            )
            documents.append(doc)
        print(f"✅ {len(documents)} 件のDocumentを作成しました。")
        return documents

    def build_database(self, documents):
        """
        Documentのリストを受け取り、ベクトル化してChromaDBに保存
        """
        print("🚀 データベースを構築中... (曲数によっては時間がかかります)")
        # ChromaDBにドキュメントを追加
        self.vectorstore.add_documents(documents)
        print("✅ データベースの構築が完了しました！")

    def run(self, file_path="data/songs.json"):
        """
        一連の処理を実行する
        """
        songs_data = self.load_songs_from_json(file_path)
        documents = self.create_documents(songs_data)
        self.build_database(documents)

# --- 実行用 ---
if __name__ == '__main__':
    # このファイルが直接実行された場合にのみ、データベースを構築する
    vectorizer = Vectorizer()
    vectorizer.run()
 # RAGを使って推薦文を生成するコアロジック
# modules/recommender.py
import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
import config

class LyricRecommender:
    def __init__(self):
        # 添付資料の「2.9. Chatbot（RAG）の起動」セルを参考
        self.embeddings = OpenAIEmbeddings(
            openai_api_base=config.OPENAI_API_BASE,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model=config.EMBED_MODEL
        )
        self.vectorstore = Chroma(
            collection_name=config.COLLECTION_NAME,
            persist_directory=config.CHROMA_DIR,
            embedding_function=self.embeddings
        )
        self.llm = ChatOpenAI(
            openai_api_base=config.OPENAI_API_BASE,
            openai_api_key=os.environ.get("OPENAI_API_KEY"),
            model=config.LLM_MODEL,
            temperature=0.5
        )
        self.prompt_template = """あなたはプロの音楽キュレーターです。
ユーザーが選んだ曲「{selected_song}」の歌詞と似た雰囲気を持つ曲を、以下の参考歌詞リストの中から3曲推薦してください。

推薦する際は、なぜその曲が似ていると感じたのか、歌詞のテーマや表現、世界観などを引用しながら、魅力的な解説を加えてください。

[参考歌詞リスト]
{context}

[あなたの推薦文]
"""

    def recommend(self, selected_song_title, selected_song_lyrics):
        # 1. 類似する歌詞を持つドキュメントをベクトル検索
        docs = self.vectorstore.similarity_search(selected_song_lyrics, k=10) # 少し多めに候補を取得

        # 2. 検索結果から自分自身を除外
        context_docs = [d for d in docs if d.metadata.get("title") != selected_song_title][:5] # 上位5件を文脈に使う
        
        if not context_docs:
            return "申し訳ありません、似ている曲を見つけられませんでした。"

        context_text = "\n\n---\n\n".join([f"曲名: {d.metadata.get('title')}\n歌詞抜粋: {d.page_content}" for d in context_docs])

        # 3. LLMにプロンプトを投げて推薦文を生成
        prompt = self.prompt_template.format(selected_song=selected_song_title, context=context_text)
        response = self.llm.invoke(prompt)
        
        return response.content
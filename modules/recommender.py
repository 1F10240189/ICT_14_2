import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.docstore.document import Document # Documentクラスをインポート
import config
from modules.external_api_clients import UnifiedMusicService

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
ユーザーが選んだ曲「{selected_song}」の歌詞や雰囲気、音響的特徴と似た曲を、以下の参考楽曲リストの中から3曲推薦してください。

推薦する際は、なぜその曲が似ていると感じたのか、歌詞のテーマ、表現、世界観、テンポ、ジャンル、楽器構成などの音響的特徴を引用しながら、魅力的な解説を加えてください。

各推薦曲について、以下の情報を可能な限り含めてください。
- 曲名
- アーティスト名
- 試聴リンク (もしあれば)
- ジャケット写真のURL (もしあれば)
- アーティストの公式サイトリンク (もしあれば)

最後に「根拠として参照した曲名」を列挙（最大5件）してください。
わからない点は「不明」と明記してください。

[参考楽曲リスト]
{context}

[あなたの推薦文]
"""

        # 新しいAPIクライアントの初期化
        self.unified_music_service = UnifiedMusicService()

    def _get_acoustic_feature(self, details, path, default="不明"):
        """Safely extracts a nested acoustic feature from the details dictionary."""
        keys = path.split(".")
        value = details.get("audio_features", {})
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return default # Path not found
            if value is None:
                return default
        return value

    def recommend(self, selected_mb_recording_id, selected_song_title, selected_artist_name, selected_song_lyrics, selected_album_art_url=None):
        # 1. 選択された曲の詳細情報をUnifiedMusicServiceから取得
        # これには歌詞、音響特徴量、プレビューURLなどが含まれる
        selected_song_details = self.unified_music_service.get_track_info(
            track_name=selected_song_title,
            artist_name=selected_artist_name
        )
        
        # 歌詞が取得できなかった場合は、app.pyから渡された歌詞を使用
        if not selected_song_details.get("lyrics"):
            selected_song_details["lyrics"] = selected_song_lyrics

        # 2. 選択された曲の歌詞を元に、ローカルDBから類似度スコア付きでドキュメントをベクトル検索
        docs_scores = self.vectorstore.similarity_search_with_relevance_scores(selected_song_details["lyrics"], k=10) 

        # 3. 検索結果から自分自身を除外し、スコアでフィルタリング
        filtered_local_docs = []
        for d, s in docs_scores:
            if d.metadata.get("title") != selected_song_title and s >= config.SCORE_THRESHOLD:
                filtered_local_docs.append((d, s))
        
        # 4. 外部APIから関連性の高い楽曲を検索・取得
        # 選択された曲のタイトルとアーティストを元に、MusicBrainzで広範な検索を行う
        mb_search_results = self.unified_music_service.search_musicbrainz_recording(f"{selected_song_title} {selected_artist_name}", limit=20) 
        
        external_candidate_songs = []
        for rec in mb_search_results:
            title = rec.get('title')
            artist_credit = rec.get('artist-credit')
            artist = artist_credit[0].get('name') if artist_credit else "Unknown Artist"
            if title != selected_song_title: # 選択された曲自身は除外
                external_candidate_songs.append({"title": title, "artist": artist, "mbid": rec.get('id')})

        # 5. ローカルと外部の候補を統合し、詳細情報を取得
        all_candidate_docs = []
        source_titles = set() # 参照元となる曲名を保持するためのセット

        # ローカルDBからの候補
        for d, s in filtered_local_docs[:5]: # 上位5件を文脈に使う
            title = d.metadata.get("title", "不明な曲名")
            artist = d.metadata.get("artist", "不明なアーティスト")
            lyrics = d.page_content
            
            # 外部APIから詳細情報を取得
            # ここではMusicBrainz IDが不明なため、タイトルとアーティストで検索
            details = self.unified_music_service.get_track_info(
                track_name=title,
                artist_name=artist
            )
            details["lyrics"] = lyrics # ローカルの歌詞を優先

            # Extract acoustic features using the helper
            tempo = self._get_acoustic_feature(details, "rhythm.bpm")
            genre = self._get_acoustic_feature(details, "tonal.key_strength") # Placeholder, actual genre might be elsewhere
            instrumentation = self._get_acoustic_feature(details, "sfx.instrumentation") # Placeholder

            all_candidate_docs.append(Document(
                page_content=f"曲名: {details["name"]}\nアーティスト: {details["artist"]}\n歌詞:\n{details["lyrics"]}\nテンポ: {tempo}\nジャンル: {genre}\n楽器構成: {instrumentation}",
                metadata={
                    "title": details["name"],
                    "artist": details["artist"],
                    "album_art_url": details["album_art_url"],
                    "preview_url": details["preview_url"],
                    "artist_official_url": None, # Added default None
                    "source_type": "local_db_and_external_api"
                }
            ))
            source_titles.add(title)

        # 外部APIからの候補 (ローカルDBと重複しないように注意)
        for song_info in external_candidate_songs:
            title = song_info["title"]
            artist = song_info["artist"]
            mbid = song_info["mbid"]
            if title not in source_titles: # 重複を避ける
                details = self.unified_music_service.get_track_info(
                    track_name=title,
                    artist_name=artist
                )
                
                # Extract acoustic features using the helper
                tempo = self._get_acoustic_feature(details, "rhythm.bpm")
                genre = self._get_acoustic_feature(details, "tonal.key_strength") # Placeholder
                instrumentation = self._get_acoustic_feature(details, "sfx.instrumentation") # Placeholder

                all_candidate_docs.append(Document(
                    page_content=f"曲名: {details["name"]}\nアーティスト: {details["artist"]}\n歌詞:\n{details["lyrics"]}\nテンポ: {tempo}\nジャンル: {genre}\n楽器構成: {instrumentation}",
                    metadata={
                        "title": details["name"],
                        "artist": details["artist"],
                        "album_art_url": details["album_art_url"],
                        "preview_url": details["preview_url"],
                        "artist_official_url": None, # Added default None
                        "source_type": "external_api"
                    }
                ))
                source_titles.add(title)

        if not all_candidate_docs:
            return "申し訳ありません、似ている曲を見つけられませんでした。外部APIからも関連する曲が見つかりませんでした。"

        # 6. LLMに渡すコンテキストを構築
        context_parts = []
        # LLMに渡すコンテキストは、最大5件程度に絞るのが一般的
        for doc in all_candidate_docs[:5]: 
            content = doc.page_content
            metadata = doc.metadata
            
            context_parts.append(f"曲名: {metadata.get("title")}\nアーティスト: {metadata.get("artist")}\n歌詞:\n{content}\n試聴: {metadata.get("preview_url", "不明")}\nジャケット: {metadata.get("album_art_url", "不明")}\n公式サイト: {metadata.get("artist_official_url", "不明")}")
            
        context_text = "\n\n---\n\n".join(context_parts)

        # 7. LLMにプロンプトを投げて推薦文を生成
        prompt = self.prompt_template.format(selected_song=selected_song_title, context=context_text)
        response = self.llm.invoke(prompt)
        
        # 8. 推薦文と参照元を結合して返す
        answer = response.content
        
        # 参照元を整形して追加
        if source_titles:
            sources_str = "\n".join([f"- {title}" for title in sorted(list(source_titles))])
            answer += f"\n\n### 根拠として参照した曲名\n{sources_str}"
        
        return answer
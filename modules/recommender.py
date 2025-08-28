import os
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_chroma import Chroma
from langchain.docstore.document import Document # Documentクラスをインポート
import config
from modules.external_api_clients import MusicBrainzClient, AcousticBrainzClient, TheAudioDBClient, iTunesSearchClient

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
        self.mb_client = MusicBrainzClient()
        self.ab_client = AcousticBrainzClient()
        self.audiodb_client = TheAudioDBClient()
        self.itunes_client = iTunesSearchClient()

    def _get_song_details_from_external_apis(self, title, artist):
        details = {
            "title": title,
            "artist": artist,
            "lyrics": "", # 外部APIから歌詞を取得するのは難しい場合が多い
            "acoustic_features": {},
            "album_art_url": "",
            "preview_url": "",
            "artist_official_url": ""
        }

        # MusicBrainzから詳細情報を取得
        mb_recordings = self.mb_client.search_recording(f"artist:{artist} AND recording:{title}", limit=1)
        if mb_recordings:
            mb_recording = mb_recordings[0]
            details["mbid"] = mb_recording.get('id')
            
            # アーティスト公式サイトリンク
            artist_id = mb_recording.get('artist-credit')[0].get('artist', {}).get('id')
            if artist_id:
                artist_info = self.mb_client.get_artist_info(artist_id)
                if artist_info and 'url-rels' in artist_info:
                    official_url = next((rel['target'] for rel in artist_info['url-rels'] if rel['type'] == 'official homepage'), None)
                    details["artist_official_url"] = official_url

        # AcousticBrainzから音響的特徴を取得 (MusicBrainz IDが必要)
        if details.get("mbid"):
            acoustic_data = self.ab_client.get_features(details["mbid"])
            if acoustic_data and 'lowlevel' in acoustic_data:
                # テンポ、ジャンル、楽器構成などを抽出
                details["acoustic_features"] = {
                    "bpm": acoustic_data['lowlevel'].get('bpm'),
                    "genre": acoustic_data.get('metadata', {}).get('tags', {}).get('genre'),
                    "instrumentation": acoustic_data.get('metadata', {}).get('tags', {}).get('instrumentation')
                }

        # TheAudioDBからジャケット写真を取得
        album_art = self.audiodb_client.search_album_image(artist, title) # Try album image first
        if not album_art:
            album_art = self.audiodb_client.search_track_image(artist, title) # Fallback to track image
        details["album_art_url"] = album_art

        # iTunes Search APIから試聴リンクを取得
        itunes_results = self.itunes_client.search_song(f"{title} {artist}", limit=1)
        if itunes_results:
            details["preview_url"] = itunes_results[0].get('previewUrl')

        return details

    def recommend(self, selected_song_title, selected_song_lyrics):
        # 1. 類似度スコア付きでドキュメントをベクトル検索 (ローカルDBから)
        # kは多めに取得し、後でスコアでフィルタリング
        docs_scores = self.vectorstore.similarity_search_with_relevance_scores(selected_song_lyrics, k=10) 

        # 2. 検索結果から自分自身を除外し、スコアでフィルタリング
        # config.SCORE_THRESHOLD を使用
        filtered_local_docs = []
        for d, s in docs_scores:
            if d.metadata.get("title") != selected_song_title and s >= config.SCORE_THRESHOLD:
                filtered_local_docs.append((d, s))
        
        # 3. 外部APIから関連性の高い楽曲を検索・取得
        # ユーザーが選択した曲のタイトルと歌詞を元に、MusicBrainzで広範な検索を行う
        # ここでは、選択された曲のタイトルをクエリとしてMusicBrainzを検索
        mb_search_results = self.mb_client.search_recording(selected_song_title, limit=20) # 20件程度取得
        
        external_candidate_songs = []
        for rec in mb_search_results:
            title = rec.get('title')
            artist_credit = rec.get('artist-credit')
            artist = artist_credit[0].get('name') if artist_credit else "Unknown Artist"
            if title != selected_song_title: # 選択された曲自身は除外
                external_candidate_songs.append({"title": title, "artist": artist})

        # 4. ローカルと外部の候補を統合し、詳細情報を取得
        all_candidate_docs = []
        source_titles = set() # 参照元となる曲名を保持するためのセット

        # ローカルDBからの候補
        for d, s in filtered_local_docs[:5]: # 上位5件を文脈に使う
            title = d.metadata.get("title", "不明な曲名")
            artist = d.metadata.get("artist", "不明なアーティスト")
            lyrics = d.page_content
            
            # 外部APIから詳細情報を取得
            details = self._get_song_details_from_external_apis(title, artist)
            details["lyrics"] = lyrics # ローカルの歌詞を優先

            all_candidate_docs.append(Document(
                page_content=f"曲名: {details["title"]}\nアーティスト: {details["artist"]}\n歌詞:\n{details["lyrics"]}\nテンポ: {details["acoustic_features"].get("bpm", "不明")}\nジャンル: {details["acoustic_features"].get("genre", "不明")}\n楽器構成: {details["acoustic_features"].get("instrumentation", "不明")}",
                metadata={
                    "title": details["title"],
                    "artist": details["artist"],
                    "album_art_url": details["album_art_url"],
                    "preview_url": details["preview_url"],
                    "artist_official_url": details["artist_official_url"],
                    "source_type": "local_db_and_external_api"
                }
            ))
            source_titles.add(title)

        # 外部APIからの候補 (ローカルDBと重複しないように注意)
        for song_info in external_candidate_songs:
            title = song_info["title"]
            artist = song_info["artist"]
            if title not in source_titles: # 重複を避ける
                details = self._get_song_details_from_external_apis(title, artist)
                
                # 歌詞がない場合は、LLMに渡すコンテキストとして不十分な場合があるため、
                # ここでは歌詞がなくても追加するが、実際のRAGでは考慮が必要
                all_candidate_docs.append(Document(
                    page_content=f"曲名: {details["title"]}\nアーティスト: {details["artist"]}\n歌詞:\n{details["lyrics"]}\nテンポ: {details["acoustic_features"].get("bpm", "不明")}\nジャンル: {details["acoustic_features"].get("genre", "不明")}\n楽器構成: {details["acoustic_features"].get("instrumentation", "不明")}",
                    metadata={
                        "title": details["title"],
                        "artist": details["artist"],
                        "album_art_url": details["album_art_url"],
                        "preview_url": details["preview_url"],
                        "artist_official_url": details["artist_official_url"],
                        "source_type": "external_api"
                    }
                ))
                source_titles.add(title)

        if not all_candidate_docs:
            return "申し訳ありません、似ている曲を見つけられませんでした。外部APIからも関連する曲が見つかりませんでした。"

        # 5. LLMに渡すコンテキストを構築
        context_parts = []
        # LLMに渡すコンテキストは、最大5件程度に絞るのが一般的
        for doc in all_candidate_docs[:5]: 
            content = doc.page_content
            metadata = doc.metadata
            
            context_parts.append(f"曲名: {metadata.get("title")}\nアーティスト: {metadata.get("artist")}\n歌詞:\n{content}\n試聴: {metadata.get("preview_url", "不明")}\nジャケット: {metadata.get("album_art_url", "不明")}\n公式サイト: {metadata.get("artist_official_url", "不明")}")
            
        context_text = "\n\n---\n\n".join(context_parts)

        # 6. LLMにプロンプトを投げて推薦文を生成
        prompt = self.prompt_template.format(selected_song=selected_song_title, context=context_text)
        response = self.llm.invoke(prompt)
        
        # 7. 推薦文と参照元を結合して返す
        answer = response.content
        
        # 参照元を整形して追加
        if source_titles:
            sources_str = "\n".join([f"- {title}" for title in sorted(list(source_titles))])
            answer += f"\n\n### 根拠として参照した曲名\n{sources_str}"
        
        return answer
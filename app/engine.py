"""
engine.py — Pinecone-powered semantic search engine (Phase 3).
================================================================================
"""

import logging
import os
import time
import threading
import uuid
import json
from typing import Callable, Dict, List, Optional

import pymupdf as fitz
from pinecone import Pinecone

from app.ocr import extract_text_hybrid, extract_visual_description, page_to_base64
from app.chunking import chunk_page

logger = logging.getLogger(__name__)

_embedding_model = None
_embedding_lock = threading.Lock()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "vision-rag")
PINECONE_INDEX_HOST = os.getenv("PINECONE_INDEX_HOST")
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
INDEX_TRACKER_FILE = os.getenv("INDEX_TRACKER_FILE", "indexed_files.json")


def _get_embedding_model():
    """Lazy-load the sentence-transformers model."""
    global _embedding_model
    if _embedding_model is None:
        with _embedding_lock:
            if _embedding_model is None:
                logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}...")
                from sentence_transformers import SentenceTransformer
                _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
                logger.info("Embedding model loaded.")
    return _embedding_model


class VisionEngine:
    """Core RAG engine with Pinecone Cloud vector search."""

    def __init__(self):
        if not PINECONE_API_KEY:
            logger.warning("PINECONE_API_KEY not set in environment.")
            self._index = None
        else:
            pc = Pinecone(api_key=PINECONE_API_KEY)
            if PINECONE_INDEX_HOST:
                self._index = pc.Index(host=PINECONE_INDEX_HOST)
            else:
                self._index = pc.Index(PINECONE_INDEX_NAME)

        # In-memory image cache (not persisted — rebuilt on demand)
        self._page_images: Dict[str, str] = {}

        # Track indexed documents via a lightweight local JSON file
        self._indexed_filenames: set = set()
        self._load_tracker()

        # Threading
        self._current_run_id = str(uuid.uuid4())
        self._lock = threading.Lock()

        logger.info(f"Enterprise VisionEngine initialized. Connected to Pinecone: {PINECONE_INDEX_NAME}")

    def _load_tracker(self):
        if os.path.exists(INDEX_TRACKER_FILE):
            try:
                with open(INDEX_TRACKER_FILE, "r") as f:
                    self._indexed_filenames = set(json.load(f))
            except Exception as e:
                logger.error(f"Failed to load index tracker: {e}")

    def _save_tracker(self):
        try:
            with open(INDEX_TRACKER_FILE, "w") as f:
                json.dump(list(self._indexed_filenames), f)
        except Exception as e:
            logger.error(f"Failed to save index tracker: {e}")

    def get_document_list(self) -> List[str]:
        with self._lock:
            return list(self._indexed_filenames)

    def remove_document(self, filename: str):
        with self._lock:
            logger.info(f"Removing document {filename} locally...")
            prefix = f"{filename}_"
            self._page_images = {k: v for k, v in self._page_images.items() if not k.startswith(prefix)}
            self._indexed_filenames.discard(filename)
            self._save_tracker()
            # Note: A full implementation would query Pinecone by metadata filter and delete the vectors.

    def load_or_create_index(self, pdf_path: str, status_callback: Optional[Callable[[str, int, str], None]] = None):
        run_id = str(uuid.uuid4())
        self._current_run_id = run_id
        filename = os.path.basename(pdf_path)

        def _report(step_id: str, progress: int, msg: str):
            if status_callback:
                status_callback(step_id, progress, msg)

        logger.info(f"Starting Pinecone indexing pipeline for {filename}")
        _report("upload", 15, "Starting extraction...")

        all_chunk_records: List[Dict] = []
        local_page_images: Dict[str, str] = {}
        doc = None

        try:
            doc = fitz.open(pdf_path)
            total = len(doc)

            for i, page in enumerate(doc):
                page_num = i + 1
                page_id = f"{filename}_{page_num}"

                if self._current_run_id != run_id:
                    return

                logger.info(f"Processing {filename} page {page_num}/{total}...")
                base_progress = 15 + int((i / total) * 50)
                _report("text", base_progress, f"Extracting text (Page {page_num}/{total})...")

                text = extract_text_hybrid(page)
                visual_desc = None
                try:
                    visual_desc = extract_visual_description(page)
                except Exception as e:
                    logger.warning(f"Page {page_num}: visual analysis failed: {e}")

                try:
                    local_page_images[page_id] = page_to_base64(page, dpi=150)
                except Exception:
                    pass

                page_chunks = chunk_page(page_text=text, visual_description=visual_desc, filename=filename, page_num=page_num)
                all_chunk_records.extend(page_chunks)

            if self._current_run_id != run_id:
                return

            _report("index", 70, f"Generating embeddings for {len(all_chunk_records)} chunks...")
            model = _get_embedding_model()
            texts_to_embed = [r["text"] for r in all_chunk_records]
            
            embeddings = model.encode(
                texts_to_embed,
                show_progress_bar=False,
                batch_size=8,
                normalize_embeddings=True,
            ).tolist()

            _report("index", 85, "Uploading to Pinecone Cloud...")

            with self._lock:
                if self._index:
                    vectors = []
                    for r, emb in zip(all_chunk_records, embeddings):
                        meta = r["metadata"]
                        # Store the raw text inside metadata so Pinecone returns it
                        meta["text"] = r["raw_text"]
                        vectors.append({"id": r["id"], "values": emb, "metadata": meta})

                    batch_size = 100
                    for batch_start in range(0, len(vectors), batch_size):
                        self._index.upsert(vectors=vectors[batch_start:batch_start + batch_size])

                self._page_images.update(local_page_images)
                self._indexed_filenames.add(filename)
                self._save_tracker()

            _report("completed", 100, f"Successfully uploaded {len(all_chunk_records)} chunks to Pinecone")

        except Exception as e:
            _report("error", 0, f"Indexing failed: {e}")
            raise
        finally:
            if doc:
                doc.close()

    def search(self, queries: List[str], k_total: int = 5, prioritize_visuals: bool = False) -> List[Dict]:
        with self._lock:
            if not self._index or not queries:
                return []

            model = _get_embedding_model()
            query_embeddings = model.encode(queries, normalize_embeddings=True).tolist()

            page_scores: Dict[str, float] = {}
            page_texts: Dict[str, List[str]] = {}
            page_info: Dict[str, Dict] = {}

            for q_embedding in query_embeddings:
                # Query Pinecone Cloud
                results = self._index.query(
                    vector=q_embedding,
                    top_k=k_total * 3,
                    include_metadata=True
                )

                if not results.matches:
                    continue

                for match in results.matches:
                    meta = match.metadata
                    if not meta: continue
                    
                    score = match.score
                    page_id = f"{meta['filename']}_{meta['page_num']}"

                    # Boost visual chunks if requested
                    boost = 1.5 if (prioritize_visuals and meta.get("chunk_type") == "visual") else 1.0
                    final_score = score * boost

                    if page_id not in page_scores or final_score > page_scores[page_id]:
                        page_scores[page_id] = final_score

                    page_info[page_id] = {"filename": meta["filename"], "page_num": int(meta["page_num"])}

                    if page_id not in page_texts:
                        page_texts[page_id] = []
                    
                    doc_text = meta.get("text", "")
                    if doc_text and doc_text not in page_texts[page_id]:
                        page_texts[page_id].append(doc_text)

            if not page_scores:
                return []

            sorted_pages = sorted(page_scores.keys(), key=lambda pid: page_scores[pid], reverse=True)[:k_total]

            results = []
            for page_id in sorted_pages:
                info = page_info[page_id]
                results.append({
                    "filename": info["filename"],
                    "page_num": info["page_num"],
                    "score": round(page_scores[page_id], 4),
                    "retrieved_chunks": page_texts.get(page_id, []),
                })

            return results

    def get_page_images(self, pages_to_fetch: List[Dict]) -> Dict[str, str]:
        with self._lock:
            result = {}
            for p in pages_to_fetch:
                page_id = f"{p['filename']}_{p['page_num']}"
                if page_id in self._page_images:
                    result[page_id] = self._page_images[page_id]
            return result

    def get_page_info(self, filename: str, page_num: int) -> Optional[Dict]:
        return None

    @property
    def is_ready(self) -> bool:
        return len(self._indexed_filenames) > 0

    @property
    def chunk_count(self) -> int:
        return 0
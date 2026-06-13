import logging
import os
import asyncio
from typing import Dict, List, Optional

import httpx

from app.ocr import extract_text_hybrid

logger = logging.getLogger(__name__)

_API_TIMEOUT = 90.0

class VisionService:
    """Generates answers using Groq API asynchronously."""

    TEXT_MODELS = [
        "llama-3.3-70b-versatile",
        "llama-3.1-8b-instant",
        "mixtral-8x7b-32768",
    ]

    VISION_MODELS = [
        os.getenv("GROQ_VISION_MODEL", "llama-3.2-90b-vision-preview"),
    ]

    API_URL = "https://api.groq.com/openai/v1/chat/completions"

    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        configured = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        self.text_models = [configured] + [m for m in self.TEXT_MODELS if m != configured]

    async def generate(self, query: str, page_numbers: List[Dict], chat_history: str, needs_rag: bool = True, engine=None) -> str:
        context_text = self._extract_context(page_numbers, engine)
        system_prompt = self._build_system_prompt(context_text, chat_history, needs_rag)

        page_images: Dict[str, str] = {}
        if needs_rag and engine and page_numbers:
            page_images = engine.get_page_images(page_numbers)

        if page_images:
            return await self._call_vision(system_prompt, query, page_images)
        else:
            return await self._call_text(system_prompt, query)

    @staticmethod
    def _extract_context(page_numbers: List[Dict], engine=None):
        if not page_numbers or not engine:
            return ""
        parts = []
        seen_pages = set()
        for p in page_numbers:
            fname = p["filename"]
            pnum = p["page_num"]
            page_key = f"{fname}_{pnum}"

            if page_key in seen_pages: continue
            seen_pages.add(page_key)

            retrieved_chunks = p.get("retrieved_chunks", [])
            if retrieved_chunks:
                chunk_text = "\n".join(retrieved_chunks)
                parts.append(f"\n--- {fname} (Page {pnum}) ---\n{chunk_text}\n")
        return "".join(parts)

    @staticmethod
    def _build_system_prompt(context: str, history: str, needs_rag: bool) -> str:
        prompt = ""
        if history and history != "No previous conversation.":
            prompt += f"Previous conversation:\n{history}\n\n"
        if context:
            prompt += f"Retrieved document context:\n{context}\n\n"
        if needs_rag:
            prompt += (
                "You are a precise document assistant with VISUAL understanding. "
                "ALWAYS answer from the retrieved document context. Do not make up information. "
                "Quote exactly as extracted."
            )
        else:
            prompt += "You are a helpful, friendly AI assistant."
        return prompt

    async def _call_text(self, system_prompt: str, user_message: str) -> str:
        for model in self.text_models:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {"model": model, "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_message}]}
                async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                    resp = await client.post(self.API_URL, headers=headers, json=payload)
                    resp.raise_for_status()
                    return resp.json().get("choices", [{}])[0].get("message", {}).get("content", "")
            except Exception as e:
                continue
        return "⚠️ All models failed. Please wait and try again."

    async def _call_vision(self, system_prompt: str, user_message: str, page_images: Dict[str, str]) -> str:
        # Simplified for brevity
        return await self._call_text(system_prompt, user_message)

    async def generate_stream(self, query: str, page_numbers: List[Dict], chat_history: str, needs_rag: bool = True, engine=None):
        context_text = self._extract_context(page_numbers, engine)
        system_prompt = self._build_system_prompt(context_text, chat_history, needs_rag)

        page_images: Dict[str, str] = {}
        if needs_rag and engine and page_numbers:
            page_images = engine.get_page_images(page_numbers)

        if page_images:
            async for chunk in self._call_vision_stream(system_prompt, query, page_images):
                yield chunk
        else:
            async for chunk in self._call_text_stream(system_prompt, query):
                yield chunk

    async def _call_text_stream(self, system_prompt: str, user_message: str):
        if not self.api_key:
            yield "⚠️ GROQ_API_KEY is not set!"
            return

        for model in self.text_models:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message}
                    ],
                    "stream": True,
                    "temperature": 0.5,
                }
                async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                    async with client.stream("POST", self.API_URL, headers=headers, json=payload) as resp:
                        resp.raise_for_status()
                        import json
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]": return
                                try:
                                    data = json.loads(data_str)
                                    delta = data.get("choices", [{}])[0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content: yield content
                                except json.JSONDecodeError:
                                    continue
                return # success
            except Exception as e:
                logger.error(f"Stream error on model {model}: {e}")
                continue
        yield "⚠️ All models failed streaming."

    async def _call_vision_stream(self, system_prompt: str, user_message: str, page_images: Dict[str, str]):
        user_content = [{"type": "text", "text": user_message}]
        for page_id, b64 in sorted(page_images.items())[:4]:
            user_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
            
        for model in self.VISION_MODELS:
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                payload = {
                    "model": model,
                    "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_content}],
                    "stream": True,
                    "temperature": 0.3,
                }
                async with httpx.AsyncClient(timeout=_API_TIMEOUT) as client:
                    async with client.stream("POST", self.API_URL, headers=headers, json=payload) as resp:
                        resp.raise_for_status()
                        import json
                        async for line in resp.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:]
                                if data_str.strip() == "[DONE]": return
                                try:
                                    data = json.loads(data_str)
                                    content = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if content: yield content
                                except json.JSONDecodeError:
                                    continue
                return
            except Exception as e:
                continue
        async for chunk in self._call_text_stream(system_prompt, user_message):
            yield chunk
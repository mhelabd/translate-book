"""Translation engine using the OpenAI API with smart batching and retries."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Callable

import tiktoken
from openai import OpenAI, RateLimitError, APITimeoutError, APIConnectionError

from .epub_handler import TextChunk

SYSTEM_PROMPT = """\
You are a professional literary translator. Your task is to translate the \
following text into clear, natural, modern English.

Rules:
1. Preserve the original meaning, tone, and style as closely as possible.
2. If the source is in Old English, Middle English, Early Modern English, or \
any archaic form of English, modernize vocabulary, grammar, and spelling while \
keeping the literary quality intact.
3. If the source is in a non-English language, translate it into fluent modern English.
4. Keep proper nouns (names, places) in their most commonly recognized English form.
5. Preserve paragraph structure — each line of the input corresponds to a \
separate paragraph or text block. Output the same number of lines.
6. Do NOT add commentary, notes, or explanations. Output ONLY the translated text.
7. Do NOT wrap the output in quotes or code blocks.
"""


@dataclass
class TranslationConfig:
    model: str = "gpt-4o-mini"
    max_tokens_per_request: int = 4000
    max_retries: int = 5
    base_delay: float = 2.0
    temperature: float = 0.3


def count_tokens(text: str, model: str = "gpt-4o-mini") -> int:
    try:
        enc = tiktoken.encoding_for_model(model)
    except KeyError:
        enc = tiktoken.get_encoding("cl100k_base")
    return len(enc.encode(text))


def translate_chunks(
    chunks: list[TextChunk],
    config: TranslationConfig | None = None,
    api_key: str | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> list[TextChunk]:
    """Translate a list of text chunks via the OpenAI API.

    Returns the same list with `translated_text` populated.
    """
    if config is None:
        config = TranslationConfig()

    key = api_key or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise EnvironmentError(
            "No OpenAI API key found. Set the OPENAI_API_KEY environment "
            "variable or pass --api-key on the command line."
        )

    client = OpenAI(api_key=key)

    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if not chunk.original_text.strip():
            chunk.translated_text = chunk.original_text
            if progress_callback:
                progress_callback(i + 1, total)
            continue

        chunk.translated_text = _translate_single(
            client, chunk.original_text, config
        )

        if progress_callback:
            progress_callback(i + 1, total)

    return chunks


def _translate_single(
    client: OpenAI, text: str, config: TranslationConfig
) -> str:
    """Call the API for a single chunk, with exponential-backoff retries."""
    for attempt in range(config.max_retries):
        try:
            response = client.chat.completions.create(
                model=config.model,
                temperature=config.temperature,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": text},
                ],
            )
            result = response.choices[0].message.content
            return result.strip() if result else text
        except (RateLimitError, APITimeoutError, APIConnectionError) as exc:
            if attempt == config.max_retries - 1:
                raise
            delay = config.base_delay * (2 ** attempt)
            time.sleep(delay)
    return text

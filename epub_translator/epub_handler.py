"""Read and write EPUB files, extracting translatable HTML content."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, NavigableString


@dataclass
class TextChunk:
    """A translatable piece of text extracted from an EPUB document."""

    item_id: str
    xpath_index: int
    original_text: str
    translated_text: str | None = None


@dataclass
class EPUBDocument:
    """Represents a parsed EPUB ready for translation."""

    book: epub.EpubBook
    text_items: list[epub.EpubHtml] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path) -> "EPUBDocument":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"EPUB file not found: {path}")
        if not path.suffix.lower() == ".epub":
            raise ValueError(f"Not an EPUB file: {path}")

        book = epub.read_epub(str(path), options={"ignore_ncx": True})
        text_items = [
            item
            for item in book.get_items()
            if item.get_type() == ebooklib.ITEM_DOCUMENT
        ]
        return cls(book=book, text_items=text_items)

    def extract_chunks(self, max_chars: int = 2000) -> list[TextChunk]:
        """Extract translatable text chunks from all HTML documents."""
        chunks: list[TextChunk] = []
        for item in self.text_items:
            item_chunks = _extract_text_from_html(item, max_chars)
            chunks.extend(item_chunks)
        return chunks

    def apply_translations(self, chunks: list[TextChunk]) -> None:
        """Write translated text back into the EPUB HTML items."""
        chunks_by_item: dict[str, list[TextChunk]] = {}
        for chunk in chunks:
            if chunk.translated_text is not None:
                chunks_by_item.setdefault(chunk.item_id, []).append(chunk)

        for item in self.text_items:
            item_id = item.get_id()
            if item_id not in chunks_by_item:
                continue
            _apply_translations_to_html(item, chunks_by_item[item_id])

    def save(self, output_path: str | Path) -> Path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        epub.write_epub(str(output_path), self.book)
        return output_path


def _extract_text_from_html(
    item: epub.EpubHtml, max_chars: int
) -> list[TextChunk]:
    """Parse an HTML item and pull out text nodes grouped into chunks."""
    content = item.get_content().decode("utf-8", errors="replace")
    soup = BeautifulSoup(content, "lxml")

    body = soup.find("body")
    if body is None:
        body = soup

    chunks: list[TextChunk] = []
    current_texts: list[str] = []
    current_len = 0
    start_index = 0
    node_index = 0

    text_nodes = list(_iter_text_nodes(body))

    for i, node in enumerate(text_nodes):
        text = node.get_text(strip=False) if hasattr(node, "get_text") else str(node)
        text = text.strip()
        if not text:
            node_index += 1
            continue

        if current_len + len(text) > max_chars and current_texts:
            combined = "\n".join(current_texts)
            if combined.strip():
                chunks.append(
                    TextChunk(
                        item_id=item.get_id(),
                        xpath_index=start_index,
                        original_text=combined,
                    )
                )
            current_texts = []
            current_len = 0
            start_index = node_index

        current_texts.append(text)
        current_len += len(text)
        node_index += 1

    if current_texts:
        combined = "\n".join(current_texts)
        if combined.strip():
            chunks.append(
                TextChunk(
                    item_id=item.get_id(),
                    xpath_index=start_index,
                    original_text=combined,
                )
            )

    return chunks


def _iter_text_nodes(element) -> Iterator:
    """Yield leaf elements that contain meaningful text."""
    BLOCK_TAGS = {
        "p", "div", "h1", "h2", "h3", "h4", "h5", "h6",
        "li", "blockquote", "td", "th", "dt", "dd",
        "figcaption", "caption", "summary",
    }
    for child in element.children:
        if isinstance(child, NavigableString):
            if child.strip():
                yield child
        elif child.name in BLOCK_TAGS:
            yield child
        else:
            yield from _iter_text_nodes(child)


def _apply_translations_to_html(
    item: epub.EpubHtml, chunks: list[TextChunk]
) -> None:
    """Replace the full body text content of an HTML item with translated text."""
    content = item.get_content().decode("utf-8", errors="replace")
    soup = BeautifulSoup(content, "lxml")

    body = soup.find("body")
    if body is None:
        body = soup

    text_nodes = list(_iter_text_nodes(body))

    translation_map: dict[int, str] = {}
    for chunk in chunks:
        if chunk.translated_text:
            lines = chunk.translated_text.split("\n")
            for offset, line in enumerate(lines):
                translation_map[chunk.xpath_index + offset] = line

    node_index = 0
    for node in text_nodes:
        text = node.get_text(strip=False) if hasattr(node, "get_text") else str(node)
        if not text.strip():
            node_index += 1
            continue

        if node_index in translation_map:
            replacement = translation_map[node_index]
            if isinstance(node, NavigableString):
                node.replace_with(NavigableString(replacement))
            else:
                node.clear()
                node.append(NavigableString(replacement))

        node_index += 1

    updated_html = str(soup)
    item.set_content(updated_html.encode("utf-8"))

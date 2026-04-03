# EPUB Translator

Translate any EPUB book into clear, modern English — including books written in Old English, Middle English, foreign languages, or any archaic dialect.

Uses the OpenAI API to produce high-quality literary translations while preserving the full EPUB structure, formatting, images, and metadata.

## Features

- **Any language in, modern English out** — French, German, Latin, Old English, Middle English, Japanese, and more.
- **Preserves EPUB structure** — styles, images, table of contents, and metadata stay intact.
- **Smart chunking** — splits text into appropriately sized pieces so translations are accurate and context-aware.
- **Progress bar** — real-time progress reporting with estimated time remaining.
- **Configurable** — choose your OpenAI model, adjust chunk size, and control the translation temperature.
- **Automatic retries** — handles API rate limits and transient errors with exponential backoff.

## Requirements

- Python 3.10+
- An [OpenAI API key](https://platform.openai.com/api-keys)

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USER/translate-book.git
cd translate-book

# Install in a virtual environment (recommended)
python -m venv .venv
source .venv/bin/activate   # On Windows: .venv\Scripts\activate

# Install the package
pip install .
```

Or install in development mode:

```bash
pip install -e .
```

## Quick Start

```bash
# Set your API key
export OPENAI_API_KEY="sk-..."

# Translate an EPUB
epub-translate beowulf.epub
```

This produces `beowulf_modern_english.epub` in the current directory.

## Usage

```
epub-translate [OPTIONS] INPUT_FILE
```

### Arguments

| Argument     | Description                |
|-------------|----------------------------|
| `INPUT_FILE` | Path to the EPUB file to translate |

### Options

| Option               | Default            | Description                                           |
|----------------------|--------------------|-------------------------------------------------------|
| `-o, --output`       | `<input>_modern_english.epub` | Output file path                          |
| `--api-key`          | `$OPENAI_API_KEY`  | OpenAI API key                                        |
| `--model`            | `gpt-4o-mini`      | OpenAI model to use                                   |
| `--chunk-size`       | `2000`             | Max characters per translation chunk                  |
| `--temperature`      | `0.3`              | Sampling temperature (lower = more deterministic)     |
| `-h, --help`         |                    | Show help and exit                                    |

### Examples

```bash
# Basic translation
epub-translate old_book.epub

# Specify output path
epub-translate book.epub -o output/translated.epub

# Use a more capable model for higher quality
epub-translate beowulf.epub --model gpt-4o

# Translate a French novel
epub-translate les_miserables.epub -o les_mis_english.epub

# Pass API key directly
epub-translate book.epub --api-key sk-your-key-here
```

## How It Works

1. **Parse** — The EPUB is unpacked and each HTML document inside it is parsed.
2. **Extract** — Text content is extracted from the HTML, split into chunks that fit within the model's context window.
3. **Translate** — Each chunk is sent to the OpenAI API with a system prompt tuned for literary translation.
4. **Reassemble** — Translated text is written back into the HTML documents, preserving all tags and formatting.
5. **Save** — The modified EPUB is saved to disk.

## Supported Languages

Any language the underlying OpenAI model supports, including but not limited to:

- Old English / Anglo-Saxon
- Middle English
- Early Modern English (Shakespeare-era)
- French, Spanish, Italian, Portuguese
- German, Dutch, Swedish, Norwegian, Danish
- Latin, Ancient Greek
- Russian, Polish, Czech
- Chinese, Japanese, Korean
- Arabic, Hebrew, Persian
- Hindi, Bengali, Tamil
- And many more

## Cost Estimate

Translation costs depend on the model and book length. Rough estimates for a 300-page novel:

| Model         | Approximate Cost |
|--------------|------------------|
| `gpt-4o-mini` | $0.50 – $2.00    |
| `gpt-4o`      | $5.00 – $15.00   |

## License

MIT

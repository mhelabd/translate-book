"""Command-line interface for epub-translate."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.panel import Panel

from .epub_handler import EPUBDocument
from .translator import TranslationConfig, translate_chunks

console = Console()


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("input_file", type=click.Path(exists=True, dir_okay=False))
@click.option(
    "-o",
    "--output",
    type=click.Path(dir_okay=False),
    default=None,
    help="Output EPUB file path. Defaults to <input>_modern_english.epub",
)
@click.option(
    "--api-key",
    default=None,
    help="API key (or set OPENAI_API_KEY / OPENROUTER_API_KEY env var).",
)
@click.option(
    "--base-url",
    default=None,
    help="Custom API base URL (e.g. https://openrouter.ai/api/v1). "
    "Auto-detected when OPENROUTER_API_KEY is set.",
)
@click.option(
    "--model",
    default="gpt-4o-mini",
    show_default=True,
    help="Model to use for translation (any OpenAI-compatible model name).",
)
@click.option(
    "--chunk-size",
    default=2000,
    show_default=True,
    help="Max characters per translation chunk.",
)
@click.option(
    "--temperature",
    default=0.3,
    show_default=True,
    help="Sampling temperature for the model (lower = more deterministic).",
)
def main(
    input_file: str,
    output: str | None,
    api_key: str | None,
    base_url: str | None,
    model: str,
    chunk_size: int,
    temperature: float,
) -> None:
    """Translate an EPUB book from any language into modern English.

    Supports Old English, Middle English, foreign languages, and more.
    Preserves the EPUB structure, formatting, and metadata.

    Works with OpenAI, OpenRouter, or any OpenAI-compatible API.

    \b
    Examples:
      epub-translate beowulf.epub
      epub-translate book.epub -o translated.epub --model gpt-4o
      OPENROUTER_API_KEY=sk-or-... epub-translate book.epub
      epub-translate book.epub --base-url https://openrouter.ai/api/v1
    """
    input_path = Path(input_file)

    if output is None:
        output = str(input_path.stem) + "_modern_english.epub"
    output_path = Path(output)

    console.print(
        Panel.fit(
            f"[bold]EPUB Translator[/bold]\n"
            f"Input:  {input_path.name}\n"
            f"Output: {output_path.name}\n"
            f"Model:  {model}",
            border_style="blue",
        )
    )

    console.print("\n[bold blue]Step 1/3:[/bold blue] Parsing EPUB...")
    try:
        doc = EPUBDocument.load(input_path)
    except (FileNotFoundError, ValueError) as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        sys.exit(1)

    console.print(
        f"  Found [green]{len(doc.text_items)}[/green] document(s) in the EPUB.\n"
    )

    console.print("[bold blue]Step 2/3:[/bold blue] Extracting text chunks...")
    chunks = doc.extract_chunks(max_chars=chunk_size)
    console.print(
        f"  Extracted [green]{len(chunks)}[/green] translatable chunk(s).\n"
    )

    if not chunks:
        console.print("[yellow]No translatable text found. Nothing to do.[/yellow]")
        sys.exit(0)

    config = TranslationConfig(
        model=model,
        temperature=temperature,
        base_url=base_url,
    )

    console.print("[bold blue]Step 3/3:[/bold blue] Translating...\n")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=40),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Translating", total=len(chunks))

        def on_progress(current: int, total: int) -> None:
            progress.update(task, completed=current)

        try:
            translate_chunks(
                chunks,
                config=config,
                api_key=api_key,
                progress_callback=on_progress,
            )
        except EnvironmentError as exc:
            console.print(f"\n[bold red]Error:[/bold red] {exc}")
            sys.exit(1)
        except Exception as exc:
            console.print(f"\n[bold red]Translation failed:[/bold red] {exc}")
            sys.exit(1)

    console.print("\n  Applying translations to EPUB...")
    doc.apply_translations(chunks)

    saved = doc.save(output_path)
    console.print(
        f"\n[bold green]Done![/bold green] Translated EPUB saved to: "
        f"[underline]{saved}[/underline]"
    )


if __name__ == "__main__":
    main()

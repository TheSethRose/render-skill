#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pypandoc-binary>=1.13"]
# ///
"""Render Markdown files to HTML, DOCX, and/or PDF.

HTML and DOCX come from pandoc (bundled by pypandoc-binary, no system install).
PDF is printed from the rendered HTML by headless Chrome/Chromium, falling back
to WeasyPrint, so PDF and HTML share one stylesheet and need no LaTeX.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import pypandoc

HERE = Path(__file__).resolve().parent.parent
CSS = HERE / "assets" / "style.css"
REFERENCE_DOCX = HERE / "assets" / "reference.docx"
FORMATS = ("html", "docx", "pdf")
MD_FROM = "gfm+implicit_figures+yaml_metadata_block+footnotes+tex_math_dollars+smart"

CHROME_CANDIDATES = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    "google-chrome",
    "chromium",
    "chromium-browser",
    "msedge",
]


def find_chrome() -> str | None:
    for c in CHROME_CANDIDATES:
        path = c if Path(c).is_file() else shutil.which(c)
        if path:
            return path
    return None


def title_args(src: Path) -> list[str]:
    # Use the file name as a fallback title; front-matter `title:` still wins.
    return ["--metadata", f"pagetitle={src.stem}"]


def render_html(src: Path, out: Path, css: Path, toc: bool) -> None:
    args = [
        "--standalone",
        "--embed-resources",
        f"--css={css}",
        "--mathml",
        "--syntax-highlighting=pygments",
        f"--resource-path={src.parent}",
        *title_args(src),
    ]
    if toc:
        args.append("--toc")
    pypandoc.convert_file(str(src), "html5", format=MD_FROM, outputfile=str(out), extra_args=args)


def render_docx(src: Path, out: Path, reference: Path | None, toc: bool) -> None:
    args = [f"--resource-path={src.parent}", "--syntax-highlighting=tango", *title_args(src)]
    if reference:
        args.append(f"--reference-doc={reference}")
    if toc:
        args.append("--toc")
    pypandoc.convert_file(str(src), "docx", format=MD_FROM, outputfile=str(out), extra_args=args)


def pdf_complete(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 100:
        return False
    with path.open("rb") as f:
        f.seek(max(0, path.stat().st_size - 1024))
        return b"%%EOF" in f.read()


def render_pdf(html: Path, out: Path) -> str:
    chrome = find_chrome()
    if chrome:
        out.unlink(missing_ok=True)
        with tempfile.TemporaryDirectory() as profile:
            # Headless Chrome sometimes writes the PDF and then never exits, so
            # wait for a complete file instead of waiting on the process.
            proc = subprocess.Popen(
                [
                    chrome,
                    "--headless=new",
                    "--disable-gpu",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-extensions",
                    "--no-pdf-header-footer",
                    f"--user-data-dir={profile}",
                    f"--print-to-pdf={out}",
                    html.as_uri(),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            deadline = time.monotonic() + 90
            try:
                while time.monotonic() < deadline:
                    if pdf_complete(out) or proc.poll() is not None:
                        break
                    time.sleep(0.2)
            finally:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        proc.kill()
        if pdf_complete(out):
            return "chrome"
    weasy = shutil.which("weasyprint")
    if weasy:
        subprocess.run([weasy, str(html), str(out)], check=True, capture_output=True, timeout=120)
        return "weasyprint"
    raise RuntimeError("PDF needs Chrome/Chromium/Edge or WeasyPrint; none found.")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("inputs", nargs="*", type=Path, help="Markdown files or directories (searched for *.md)")
    p.add_argument("-f", "--formats", default="html,docx,pdf", help="Comma list of html,docx,pdf (default: all)")
    p.add_argument("-o", "--out-dir", type=Path, help="Output directory (default: next to each source)")
    p.add_argument("--css", type=Path, default=CSS, help="Stylesheet for HTML and PDF")
    p.add_argument("--reference-docx", type=Path, default=REFERENCE_DOCX if REFERENCE_DOCX.is_file() else None, help="Word reference doc for DOCX styles (default: bundled)")
    p.add_argument("--init-reference-docx", type=Path, metavar="PATH", help="Write pandoc's default reference.docx to PATH and exit")
    p.add_argument("--toc", action="store_true", help="Add a table of contents")
    p.add_argument("-r", "--recursive", action="store_true", help="Recurse into directories")
    a = p.parse_args()

    if a.init_reference_docx:
        data = subprocess.run(
            [pypandoc.get_pandoc_path(), "--print-default-data-file", "reference.docx"],
            check=True,
            capture_output=True,
        ).stdout
        a.init_reference_docx.write_bytes(data)
        print(f"ok   {a.init_reference_docx}")
        return 0
    if not a.inputs:
        p.error("no input files")

    formats = [f.strip().lower() for f in a.formats.split(",") if f.strip()]
    bad = [f for f in formats if f not in FORMATS]
    if bad:
        p.error(f"unknown format(s): {', '.join(bad)}")

    sources: list[Path] = []
    for item in a.inputs:
        if item.is_dir():
            sources += sorted(item.rglob("*.md") if a.recursive else item.glob("*.md"))
        elif item.is_file():
            sources.append(item)
        else:
            print(f"skip: {item} not found", file=sys.stderr)
    if not sources:
        print("No Markdown files found.", file=sys.stderr)
        return 1

    failures = 0
    for src in sources:
        src = src.resolve()
        out_dir = (a.out_dir or src.parent).resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = out_dir / src.stem
        for fmt in formats:
            target = stem.with_suffix(f".{fmt}")
            try:
                if fmt == "html":
                    render_html(src, target, a.css.resolve(), a.toc)
                    print(f"ok   {target}")
                elif fmt == "docx":
                    render_docx(src, target, a.reference_docx, a.toc)
                    print(f"ok   {target}")
                else:
                    html = stem.with_suffix(".html")
                    temp = None
                    if "html" not in formats or not html.is_file():
                        temp = tempfile.NamedTemporaryFile(suffix=".html", dir=out_dir, delete=False)
                        temp.close()
                        html = Path(temp.name)
                        render_html(src, html, a.css.resolve(), a.toc)
                    try:
                        engine = render_pdf(html, target)
                    finally:
                        if temp:
                            html.unlink(missing_ok=True)
                    print(f"ok   {target} (via {engine})")
            except Exception as e:  # report and keep going with other files
                failures += 1
                print(f"FAIL {target}: {e}", file=sys.stderr)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

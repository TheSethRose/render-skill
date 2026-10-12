---
name: render
description: Render Markdown files to styled HTML, Word (DOCX), and PDF. Use when the user invokes `/render` or asks to convert, export, or render .md files into HTML, DOCX, or PDF. Not for editing existing Word/PDF files or authoring new documents from scratch.
---

# Render

Convert Markdown into shareable documents with the bundled script. It needs only [`uv`](https://docs.astral.sh/uv/) (pandoc ships inside the `pypandoc-binary` dependency) and, for PDF, Chrome/Chromium/Edge or WeasyPrint. Paths below are relative to this skill's directory.

```bash
uv run scripts/render.py <file.md|dir> [more…] [options]
```

Options: `-f html,docx,pdf` (default all three), `-o DIR` (default: next to each source), `-r` (recurse directories), `--toc`, `--css FILE` (HTML/PDF styling), `--reference-docx FILE` (Word styles).

## Choosing inputs and formats

- `/render path/to/file.md` → render that file to all three formats.
- `/render` with no argument → use the Markdown file the conversation is about (just written or edited). If several are plausible, ask which; if none, ask for a path.
- Honor any formats or output directory the user names ("just a PDF" → `-f pdf`).
- Outputs overwrite same-named `.html/.docx/.pdf` next to the source. If one exists and wasn't produced by this skill earlier in the session, mention it before overwriting or use `-o`.

## Behavior worth knowing

- Input is GitHub-flavored Markdown plus YAML front matter (`title`, `subtitle`, `author`, `date` become the document header), footnotes, `$math$`, and smart quotes.
- Design: editorial and quiet. HTML/PDF use Charter for reading, Inter for headings and labels, one ink-blue accent, and fall back to Georgia/system fonts where those aren't installed. HTML is self-contained (CSS, images embedded) and follows light/dark mode. PDF is printed from the same HTML with print sizing and page numbers.
- DOCX uses the bundled `assets/reference.docx` (Georgia body, Aptos headings, Consolas code: fonts recipients have). Rebuild it with `uv run scripts/build_reference_docx.py` after changing its palette or fonts.
- Relative image paths resolve from the source file's folder.
- To change the look, edit `assets/style.css` or pass `--css`. For a different Word style, pass `--reference-docx` (`--init-reference-docx ref.docx` writes pandoc's plain default to start from).

## After rendering

The script prints `ok`/`FAIL` per output and exits non-zero on any failure. Report the output paths and any failures. Open or share the files only if the user asks or it's clearly wanted.

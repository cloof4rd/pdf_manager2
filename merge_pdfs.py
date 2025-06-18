import json
import argparse
import re
from pathlib import Path
from PyPDF2 import PdfMerger

CONFIG = "priority_config.json"
NUMBER_RE = re.compile(r"(\d+)")

def load_config():
    with open(CONFIG, "r") as f:
        cfg = json.load(f)
    return (
        cfg.get("batch_order", []),
        cfg.get("keyword_order", []),
        cfg.get("numeric_sort", "asc"),
    )

def make_sort_key(batch_order, keyword_order, numeric_sort):
    batch_index = {b: i for i, b in enumerate(batch_order)}
    kw_index    = {k: i for i, k in enumerate(keyword_order)}

    def key(path: Path):
        stem = path.stem
        parts = stem.split("_", 1)
        batch = parts[0]
        rest  = parts[1] if len(parts) > 1 else ""
        bpos  = batch_index.get(batch, len(batch_order))
        kpos  = next((kw_index[k] for k in keyword_order if k in rest),
                     len(keyword_order))
        m     = NUMBER_RE.search(stem)
        num   = int(m.group(1)) if m else 0
        nval  = num if numeric_sort == "asc" else -num
        return (bpos, kpos, nval, stem.lower())

    return key

def main():
    p = argparse.ArgumentParser(
        description="Merge PDFs by batch & keyword priority"
    )
    p.add_argument("folder", help="Folder containing your PDFs")
    p.add_argument(
        "-o", "--output",
        default="merged_output.pdf",
        help="Output PDF filename",
    )
    args = p.parse_args()

    batch_order, keyword_order, numeric_sort = load_config()
    sort_key = make_sort_key(batch_order, keyword_order, numeric_sort)

    pdfs = sorted(Path(args.folder).glob("*.pdf"), key=sort_key)
    merger = PdfMerger()
    for pdf in pdfs:
        merger.append(str(pdf))
    merger.write(args.output)
    merger.close()
    print(f"Merged {len(pdfs)} files into {args.output}")

if __name__ == "__main__":
    main()

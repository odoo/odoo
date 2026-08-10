#!/usr/bin/env python3
"""Benchmark three OCR engines on scanned invoices.

Engines compared (see docs/adr-002-ocr-engine.md):

1. Tesseract (local, free) — pdf2image renders each PDF page at a given DPI,
   then pytesseract runs with ``--psm 6`` / ``--psm 11`` / ``--psm 6`` at a
   different DPI. Per-word confidence comes from ``image_to_data`` (one OCR
   pass yields both the text and the per-word ``conf`` array).
2. AWS Textract ``analyze_expense`` — IAM must allow ``textract:AnalyzeExpense``.
   Costed at $0.01/page (first 1M pages, us-east-1).
3. Claude reading the PDF natively as a ``document`` block — no OCR step at
   all; the model reads pixels/layout directly. Costed at Claude Opus 4 rates
   (same constants as custom_addons/invoice_agent/models/llm_service.py).

Accuracy is character-level: ``difflib.SequenceMatcher.ratio`` between the
normalized engine output and the ground-truth text for that invoice.

Usage — inside the rebuilt odoo container, with the benchmark scans generated:

    # generate 10 synthetic scanned invoices + ground truth, then benchmark
    python scripts/bench_ocr.py --generate 10 --json /tmp/bench_results.json

    # benchmark real scans: /scans/INV-001.pdf ... plus /scans/INV-001.txt ground truth
    python scripts/bench_ocr.py --scans-dir /scans --engines tesseract_psm6,claude

Output: a markdown table on stdout (copy-paste into the ADR) and the full
per-document JSON result.
"""

import argparse
import base64
import json
import logging
import os
import random
import sys
import time
from datetime import date, timedelta
from difflib import SequenceMatcher

# ---------------------------------------------------------------------------
# Cost constants — USD per unit. Sources: AWS pricing page (Textract,
# AnalyzeExpense = $0.01/page first 1M), llm_service.py (Claude Opus 4.8).
# ---------------------------------------------------------------------------
TEXTRACT_EXPENSE_PRICE_PER_PAGE = 0.01   # USD per page, first 1M pages
CLAUDE_INPUT_PER_MT = 15.0                # USD per 1M input tokens
CLAUDE_OUTPUT_PER_MT = 75.0               # USD per 1M output tokens

CLAUDE_MODEL = os.environ.get("BENCH_CLAUDE_MODEL", "claude-opus-4-8")
CLAUDE_MAX_TOKENS = 4096

A4_PAGE = (2480, 3508)  # A4 @ 300 dpi

_logger = logging.getLogger("bench_ocr")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


# ---------------------------------------------------------------------------
# Ground-truth generation — synthetic "scanned" invoices
# ---------------------------------------------------------------------------
def _find_font(size):
    """Return a truetype font from the usual Debian/Ubuntu locations."""
    from PIL import ImageFont

    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _render_invoice(index):
    """Render one synthetic scanned invoice page; returns (text, image)."""
    from PIL import Image, ImageDraw

    vendors = [
        ("Al-Nile Trading Co.", "15 Ramses St, Cairo, Egypt", "VAT 310-456-789"),
        ("Delta Supplies GmbH", "Industriestr. 42, 40210 Düsseldorf", "DE 812345678"),
        ("Mediterranean Foods SARL", "12 Rue des Oliviers, Casablanca", "MA 00234567"),
        ("Blue Horizon Logistics", "Unit 7 Harbour Yard, Rotterdam", "NL 803456789B01"),
        ("Sahara Industrial Parts", "KM 28 Alex Desert Rd, Giza", "VAT 287-654-321"),
        ("Oasis Energy Solutions", "88 Nasr Rd, New Cairo", "VAT 299-123-876"),
        ("Nile Textiles Exporters", "6 El-Merghany St, Heliopolis", "VAT 245-778-991"),
        ("Pharos Equipment Co.", "Borg El Arab Industrial Zone", "VAT 233-456-120"),
        ("Lotus Foodstuff Distributor", "10 Talaat Harb Sq, Alexandria", "VAT 276-889-345"),
        ("Cairo Electromechanical", "5 Abbassia Main St, Cairo", "VAT 250-345-678"),
    ]
    items = [
        ("Steel pipe 3/4 inch, galvanized", "piece", 120, 4.75),
        ("Brass gate valve DN50", "piece", 25, 38.20),
        ("PVC conduit 20mm, 3m length", "bundle", 40, 6.10),
        ("Copper wire 2.5mm2, 100m roll", "roll", 15, 54.90),
        ("LED panel light 40W", "unit", 30, 22.75),
        ("Distribution board 12-way", "unit", 8, 89.30),
        ("Cable tray 200x50, 3m", "length", 22, 31.45),
        ("Circuit breaker 32A 3P", "piece", 35, 27.60),
        ("Wall socket 16A, white", "piece", 80, 3.95),
        ("Electrical tape, 10-pack", "pack", 60, 2.30),
    ]
    vendor = vendors[index % len(vendors)]
    chosen = random.sample(items, k=random.randint(3, 5))
    lines = []
    for name, unit, qty, price in chosen:
        lines.append(
            f"{name:<46} {unit:<6} {qty:>5.2f} x {price:>7.2f} = {qty * price:>9.2f}"
        )

    subtotal = sum(qty * price for _, _, qty, price in chosen)
    tax = round(subtotal * 0.14, 2)
    total = round(subtotal + tax, 2)
    issue = date(2025, 6, 1) + timedelta(days=index * 13)
    due = issue + timedelta(days=30)

    text_lines = [
        vendor[0],
        vendor[1],
        vendor[2],
        "",
        "INVOICE",
        "",
        f"Invoice No: INV-2025-{6100 + index}",
        f"Invoice Date: {issue.isoformat()}",
        f"Due Date: {due.isoformat()}",
        "",
        "Bill To:",
        "Customer Services Dept",
        "Attn: Procurement Manager",
        "",
    ] + lines + [
        "",
        f"Subtotal: {subtotal:.2f}",
        f"VAT 14%: {tax:.2f}",
        f"TOTAL: {total:.2f}",
        "",
        "Terms: net 30 days. Bank: NBE Giza, IBAN EG38 0019 0000 1234 5678.",
        "Thank you for your business.",
    ]
    ground_truth = "\n".join(text_lines)

    image = Image.new("RGB", A4_PAGE, "white")
    draw = ImageDraw.Draw(image)
    font = _find_font(34)
    y = 120
    for line in text_lines:
        draw.text((140, y), line, fill="black", font=font)
        y += 58

    return ground_truth, image


def _degrade(image, level):
    """Apply realistic scan degradation (0 = clean, 2 = heavy)."""
    from PIL import ImageFilter, ImageOps

    if level >= 1:
        image = image.convert("L").convert("RGB")
    if level >= 2:
        image = image.filter(ImageFilter.GaussianBlur(radius=0.8))
        image = ImageOps.autocontrast(image)
    return image


def generate_scans(scans_dir, count=10):
    """Create synthetic scanned invoices + .txt ground truth. Returns pairs."""
    os.makedirs(scans_dir, exist_ok=True)
    random.seed(2026)
    created = []
    for index in range(count):
        ground_truth, image = _render_invoice(index)
        # 3 of 10 scans are degraded on purpose — they become the "worst
        # scans" whose per-word confidence the ADR discusses.
        image = _degrade(image, 2 if index >= 7 else 0)
        pdf_path = os.path.join(scans_dir, f"scan-{index + 1:02d}.pdf")
        gt_path = os.path.join(scans_dir, f"scan-{index + 1:02d}.txt")
        image.save(pdf_path, "PDF", resolution=300.0)
        with open(gt_path, "w", encoding="utf-8") as handle:
            handle.write(ground_truth)
        created.append((pdf_path, gt_path))
    return created


# ---------------------------------------------------------------------------
# Normalization + scoring
# ---------------------------------------------------------------------------
def normalize(text):
    """Lowercase and collapse whitespace so layout noise doesn't dominate."""
    return " ".join((text or "").lower().split())


def char_accuracy(ground_truth, ocr_text):
    """Character-level accuracy 0..1 via SequenceMatcher on normalized text."""
    if not ground_truth and not ocr_text:
        return 1.0
    return SequenceMatcher(None, normalize(ground_truth), normalize(ocr_text)).ratio()


# ---------------------------------------------------------------------------
# Engines — each returns (text, metrics_dict, error_str)
# ---------------------------------------------------------------------------
def tesseract_extract(pdf_path, psm, dpi):
    """pdf2image -> pytesseract on every page; returns (text, mean_conf)."""
    from pdf2image import convert_from_path

    import pytesseract

    images = convert_from_path(pdf_path, dpi=dpi)
    text_parts = []
    confs = []
    for image in images:
        data = pytesseract.image_to_data(
            image,
            config=f"--psm {psm} --oem 3",
            output_type=pytesseract.Output.DICT,
        )
        words = data.get("text") or []
        conf = data.get("conf") or []
        line_text = []
        for index, word in enumerate(words):
            if not (word or "").strip():
                continue
            value = conf[index] if index < len(conf) else -1
            if value >= 0:
                confs.append(value / 100.0)
            line_text.append(word)
        text_parts.append(" ".join(line_text))
    text = "\n".join(part for part in text_parts if part.strip())
    return text, sum(confs) / len(confs) if confs else 0.0


def textract_extract(pdf_path):
    """AWS Textract AnalyzeExpense -> (text, mean_conf, summary_dict, pages)."""
    import boto3

    with open(pdf_path, "rb") as handle:
        pdf_bytes = handle.read()
    client = boto3.client(
        "textract",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
    )
    response = client.analyze_expense(Document={"Bytes": pdf_bytes})
    blocks = response.get("Blocks", [])
    line_blocks = sorted(
        (block for block in blocks if block.get("BlockType") == "LINE"),
        key=lambda block: (
            block.get("Page", 1),
            (block.get("Geometry", {}).get("BoundingBox", {}) or {}).get("Top", 0),
            (block.get("Geometry", {}).get("BoundingBox", {}) or {}).get("Left", 0),
        ),
    )
    text = "\n".join(block.get("Text", "") for block in line_blocks)
    confs = [block.get("Confidence", 0) / 100.0 for block in line_blocks]
    mean_conf = sum(confs) / len(confs) if confs else 0.0
    summary = {}
    for document in response.get("ExpenseDocuments", []):
        for field in document.get("SummaryFields", []):
            key = (field.get("LabelDetection") or {}).get("Text")
            value = (field.get("ValueDetection") or {}).get("Text")
            if key:
                summary[key] = value
    pages = len(set(block.get("Page", 1) for block in blocks))
    return text, {"confidence": round(mean_conf, 4), "pages": pages, "summary": summary}


def claude_extract(pdf_path):
    """Claude reading the PDF natively as a document block.

    Returns (text, metrics) where metrics includes the metered token usage
    and the computed USD cost at Opus 4 rates.
    """
    import anthropic

    with open(pdf_path, "rb") as handle:
        pdf_b64 = base64.b64encode(handle.read()).decode("ascii")
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY"),
        max_retries=2,
    )
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=CLAUDE_MAX_TOKENS,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {
                        "type": "text",
                        "text": (
                            "Transcribe this vendor invoice verbatim, preserving "
                            "line order, amounts, dates and VAT numbers. Output "
                            "plain text only, no commentary.",
                        ),
                    },
                ],
            },
        ],
    )
    text = "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    )
    usage = response.usage
    cost = (
        (getattr(usage, "input_tokens", 0) or 0) * CLAUDE_INPUT_PER_MT
        + (getattr(usage, "output_tokens", 0) or 0) * CLAUDE_OUTPUT_PER_MT
    ) / 1_000_000
    return text, {
        "cost_usd": round(cost, 6),
        "model": response.model,
        "input_tokens": getattr(usage, "input_tokens", None),
        "output_tokens": getattr(usage, "output_tokens", None),
    }


def run_engine(name, pdf_path):
    """Run one engine on one PDF; returns (metrics_dict, error_str)."""
    start = time.perf_counter()
    try:
        if name == "textract":
            text, metrics = textract_extract(pdf_path)
        elif name == "claude":
            text, metrics = claude_extract(pdf_path)
        elif name.startswith("tesseract"):
            parts = name.split("_")
            psm = int(parts[1].replace("psm", ""))
            dpi = int(parts[2].replace("dpi", "")) if len(parts) > 2 else 300
            text, confidence = tesseract_extract(pdf_path, psm=psm, dpi=dpi)
            metrics = {"confidence": round(confidence, 4)}
        else:
            raise ValueError(f"unknown engine {name!r}")
    except Exception as exc:
        elapsed = time.perf_counter() - start
        _logger.warning("engine %s failed on %s: %s", name, pdf_path, exc)
        return {"elapsed_s": round(elapsed, 3), "error": str(exc)[:500]}, str(exc)

    elapsed = time.perf_counter() - start
    metrics.update(
        {
            "engine": name,
            "elapsed_s": round(elapsed, 3),
            "char_len": len(text),
        }
    )
    return metrics, None, text


# ---------------------------------------------------------------------------
# Markdown table output
# ---------------------------------------------------------------------------
def render_table(results, engines):
    """Render per-doc accuracy% / latency-s cells plus an average row."""
    header = ["Doc"] + [f"{name}<br>acc% / s" for name in engines]
    lines = ["| " + " | ".join(header) + " |"]
    lines.append("|" + "---|" * (len(header) + 1))
    sums = {name: [0.0, 0.0, 0] for name in engines}  # acc, latency, valid
    for row in results:
        cells = [row["doc"]]
        for name in engines:
            entry = row.get(name, {})
            if "error" in entry:
                cells.append("ERR")
                continue
            cells.append(f"{entry['accuracy'] * 100:.1f}% / {entry['elapsed_s']:.2f}s")
            sums[name][0] += entry["accuracy"]
            sums[name][1] += entry["elapsed_s"]
            sums[name][2] += 1
        lines.append("| " + " | ".join(cells) + " |")
    avg_cells = ["**Average**"]
    for name in engines:
        count = sums[name][2]
        if not count:
            avg_cells.append("n/a")
            continue
        avg_cells.append(
            f"**{sums[name][0] / count * 100:.1f}% / {sums[name][1] / count:.2f}s**"
        )
    lines.append("| " + " | ".join(avg_cells) + " |")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--generate", type=int, metavar="N",
        help="generate N synthetic scanned invoices + ground truth first",
    )
    parser.add_argument("--scans-dir", default="/tmp/bench_scans")
    parser.add_argument("--gt-dir", default=None, help="defaults to --scans-dir")
    parser.add_argument(
        "--engines",
        default="tesseract_psm6,tesseract_psm11,tesseract_psm6_dpi150,textract,claude",
    )
    parser.add_argument("--json", default="/tmp/bench_results.json")
    args = parser.parse_args(argv)

    if args.generate:
        pairs = generate_scans(args.scans_dir, args.generate)
    else:
        gt_dir = args.gt_dir or args.scans_dir
        pairs = []
        for name in sorted(os.listdir(args.scans_dir)):
            if not name.lower().endswith(".pdf"):
                continue
            gt_path = os.path.join(gt_dir, os.path.splitext(name)[0] + ".txt")
            if not os.path.exists(gt_path):
                _logger.warning("no ground truth for %s — skipping", name)
                continue
            pairs.append((os.path.join(args.scans_dir, name), gt_path))
    if not pairs:
        parser.error("no scans found — use --generate or point --scans-dir at PDFs")

    engines = [name.strip() for name in args.engines.split(",") if name.strip()]

    # Full-data pass: run every engine, capture text + metrics, score accuracy.
    results = []
    for pdf_path, gt_path in pairs:
        with open(gt_path, encoding="utf-8") as handle:
            ground_truth = handle.read()
        doc_result = {"doc": os.path.basename(pdf_path), "pages": 1}
        for name in engines:
            metrics, error, text = run_engine(name, pdf_path)
            if error:
                doc_result[name] = {"error": error, "elapsed_s": metrics["elapsed_s"]}
                continue
            metrics["accuracy"] = round(char_accuracy(ground_truth, text), 4)
            if name == "textract":
                # Cost per call = $0.01 x pages (single-page scans here).
                metrics["cost_usd"] = round(
                    TEXTRACT_EXPENSE_PRICE_PER_PAGE * metrics.get("pages", 1), 6
                )
            else:
                metrics.setdefault("cost_usd", 0.0)
            doc_result[name] = metrics
        results.append(doc_result)

    with open(args.json, "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)
    print(render_table(results, engines))
    print("\nFull JSON written to", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())

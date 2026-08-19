#!/usr/bin/env python3
"""Generate synthetic invoice PDFs for load testing.

Usage:
    python scripts/generate_test_invoices.py
    python scripts/generate_test_invoices.py --count 20 --output invoice-ai/tests/fixtures
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfgen import canvas

    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


VENDORS = [
    {"name": "Acme Corp", "vat": "US123456789"},
    {"name": "Global Supplies Ltd", "vat": "GB987654321"},
    {"name": "TechParts GmbH", "vat": "DE555123456"},
    {"name": "Office Express SA", "vat": "FR881234567"},
    {"name": "Nordic Materials AB", "vat": "SE123456789012"},
    {"name": "BuildRight Inc", "vat": "CA123456789"},
    {"name": "CleanWater Systems", "vat": "AU123456789"},
    {"name": "SafeNet Security", "vat": "NL123456789B01"},
    {"name": "GreenEnergy Partners", "vat": "NO123456789"},
    {"name": "Pacific Trading Co", "vat": "JP123456789"},
]

LINE_ITEMS = [
    ("Office paper A4 (5 reams)", "610000", 24.99),
    ("Printer toner cartridge", "610001", 89.50),
    ("Ergonomic desk chair", "610002", 349.00),
    ("USB-C hub adapter", "610003", 45.99),
    ("Network cable Cat6 (50m)", "610004", 29.99),
    ("Monitor stand adjustable", "610005", 79.00),
    ("Wireless keyboard", "610006", 59.99),
    ("External SSD 1TB", "610007", 129.99),
    ("Webcam HD 1080p", "610008", 69.99),
    ("Standing desk converter", "610009", 199.00),
    ("Whiteboard markers (12pk)", "610010", 12.50),
    ("Paper shredder", "610011", 159.00),
    ("LED desk lamp", "610012", 39.99),
    ("Cable management tray", "610013", 24.99),
    ("Noise cancelling headphones", "610014", 249.00),
]

CURRENCIES = ["USD", "EUR", "GBP"]


def generate_invoice(c: canvas.Canvas, index: int) -> None:
    """Draw a single-page invoice PDF."""
    vendor = random.choice(VENDORS)
    currency = random.choice(CURRENCIES)
    num_lines = random.randint(1, 6)
    selected_lines = random.sample(LINE_ITEMS, min(num_lines, len(LINE_ITEMS)))

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, 270 * mm, f"INVOICE")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, 260 * mm, f"Invoice #: INV-{index:05d}")
    c.drawString(150 * mm, 270 * mm, f"Date: 2026-08-{15 + (index % 15):02d}")
    c.drawString(150 * mm, 260 * mm, f"Due: 2026-09-{15 + (index % 15):02d}")

    # Vendor info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(20 * mm, 240 * mm, "From:")
    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, 232 * mm, vendor["name"])
    c.drawString(20 * mm, 224 * mm, f"VAT: {vendor['vat']}")

    # Line items table
    y = 200 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(20 * mm, y, "Description")
    c.drawString(120 * mm, y, "Qty")
    c.drawString(140 * mm, y, "Price")
    c.drawString(170 * mm, y, "Total")
    y -= 3 * mm
    c.line(20 * mm, y, 195 * mm, y)
    y -= 5 * mm

    c.setFont("Helvetica", 10)
    subtotal = 0.0
    for desc, _account, price in selected_lines:
        qty = random.randint(1, 10)
        line_total = qty * price
        subtotal += line_total
        c.drawString(20 * mm, y, desc[:40])
        c.drawString(120 * mm, y, str(qty))
        c.drawString(140 * mm, y, f"{price:.2f}")
        c.drawString(170 * mm, y, f"{line_total:.2f}")
        y -= 6 * mm

    tax_rate = 0.10
    tax = subtotal * tax_rate
    total = subtotal + tax

    y -= 5 * mm
    c.line(120 * mm, y, 195 * mm, y)
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 10)
    c.drawString(120 * mm, y, "Subtotal:")
    c.drawString(170 * mm, y, f"{subtotal:.2f}")
    y -= 6 * mm
    c.drawString(120 * mm, y, "Tax (10%):")
    c.drawString(170 * mm, y, f"{tax:.2f}")
    y -= 6 * mm
    c.setFont("Helvetica-Bold", 12)
    c.drawString(120 * mm, y, f"TOTAL {currency}:")
    c.drawString(170 * mm, y, f"{total:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate test invoice PDFs")
    parser.add_argument(
        "--count", type=int, default=10, help="Number of PDFs to generate"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="invoice-ai/tests/fixtures",
        help="Output directory",
    )
    args = parser.parse_args()

    if not HAS_REPORTLAB:
        print("ERROR: reportlab is required. Install with: pip install reportlab")
        raise SystemExit(1)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(args.count):
        path = output_dir / f"test-invoice-{i:03d}.pdf"
        c_pdf = canvas.Canvas(str(path), pagesize=A4)
        generate_invoice(c_pdf, i)
        c_pdf.save()
        print(f"  Created {path}")

    print(f"\nGenerated {args.count} test invoices in {output_dir}/")


if __name__ == "__main__":
    main()

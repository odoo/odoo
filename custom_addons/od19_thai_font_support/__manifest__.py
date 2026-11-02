# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "OD19 Thai Font & UI Localization",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "category": "Localization",
    "summary": "Thai font support (Sarabun) for Web UI and QWeb reports",
    "description": """
OD19 Thai Font & UI Localization
================================

Provides Thai font support across all parts of the Odoo 19 system:

* **Web UI (Backend/Frontend)**: Overrides the default font with Sarabun
  (with Noto Sans Thai and system fallbacks) for consistent Thai rendering.
* **QWeb Reports (Odoo 19 Native PDF)**: Injects Sarabun into the report
  stylesheet so PDF output renders Thai correctly. The bundled TTF font files
  are referenced via ``@font-face`` so no server-side font installation is
  required for PDF generation.
* **Font files bundled**: Sarabun Regular, Bold, Italic, Bold Italic are
  shipped inside this module (``static/src/fonts/``).

This module intentionally does **not** allow per-user font switching in order
to keep the UI consistent and easy to maintain, as defined in the program
Thai Localization Strategy (Wave 0).
    """,
    "depends": ["web"],
    "assets": {
        "web.assets_backend": [
            "od19_thai_font_support/static/src/css/fonts.css",
            "od19_thai_font_support/static/src/css/backend.css",
        ],
        "web.assets_frontend": [
            "od19_thai_font_support/static/src/css/fonts.css",
            "od19_thai_font_support/static/src/css/backend.css",
        ],
        "web.report_assets_common": [
            "od19_thai_font_support/static/src/css/fonts.css",
            "od19_thai_font_support/static/src/css/report.css",
        ],
        "web.report_assets_pdf": [
            "od19_thai_font_support/static/src/css/fonts.css",
            "od19_thai_font_support/static/src/css/report.css",
        ],
    },
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_thai_font_support/static/description/icon.svg",
}

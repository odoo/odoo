# -*- coding: utf-8 -*-
{
    "name": "SEMSA Theme",
    "summary": "Institutional, public sector, municipality, health, services",
    "description": "Tema institucional de website integrado ao seletor de temas do Odoo.",
    "version": "19.0.1.0.0",
    "category": "Theme/Corporate",
    "sequence": 110,
    "author": "Kodoo",
    "website": "https://kodoo.online",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "data/generate_primary_template.xml",
        "data/theme_semsa_assets.xml",
        "views/images.xml",
    ],
    "images": [
        "static/description/theme_semsa_poster.webp",
        "static/description/theme_semsa_screenshot.webp",
    ],
    "configurator_snippets": {
        "homepage": [
            "s_cover",
            "s_text_image",
            "s_three_columns",
            "s_call_to_action",
        ],
    },
    "installable": True,
}

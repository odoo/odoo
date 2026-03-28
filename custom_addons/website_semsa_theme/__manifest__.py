# -*- coding: utf-8 -*-
{
    "name": "SEMSA Website Theme Legacy",
    "summary": "Legado substituido pelo theme_semsa",
    "version": "19.0.1.0.0",
    "category": "Website/Theme",
    "author": "Kodoo",
    "website": "https://kodoo.online",
    "license": "LGPL-3",
    "depends": ["website"],
    "data": [
        "views/website_homepage.xml",
        "data/website_theme_apply.xml",
    ],
    "assets": {
        "web.assets_frontend": [
            "website_semsa_theme/static/src/scss/website_semsa.scss",
        ],
    },
    "images": [
        "static/src/img/hero-painting.svg",
    ],
    "installable": False,
    "application": False,
}

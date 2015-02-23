# -*- coding: utf-8 -*-

{
    'name': 'Website Forum SEO',
    'category': 'Website',
    'summary': 'Website Forum automatic keyword replacement for SEO',
    'version': '1.0',
    'description': """
Replace keyword to the SEO friendly word
=====================================

Purpose of this module for improving the Forum Que/Ans description more descriptive with SEO friendly.
    * Forum SEO module store keywords.
    * keywords, SEO friendly word along with optional URL.
    * You can matches only case sensitive word.
        """,
    'author': 'Odoo SA',
    'depends': ['website_forum', 'marketing'],
    'data': [
        'views/forum_seo.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
        'data/forum_seo_demo.xml'
    ]
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documentation',
    'category': 'Website',
    'summary': 'Build a documentation/FAQ from forum questions',
    'description': """
Push the most relevant questions published on the forum to a documentation index/FAQ.
    """,
    'depends': [
        'website_forum'
    ],
    'data': [
        'data/doc_data.xml',
        'security/ir.model.access.csv',
        'views/doc.xml',
        'views/website_doc.xml',
    ],
    'demo': [
        'data/doc_demo.xml',
    ],
}

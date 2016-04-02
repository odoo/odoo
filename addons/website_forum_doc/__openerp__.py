# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documentation',
    'category': 'Website',
    'summary': 'Forum, Documentation',
    'version': '1.0',
    'description': """
Documentation based on question and pertinent answers of Forum
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
    'installable': True,
}

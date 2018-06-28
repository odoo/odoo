# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documentation',
    'category': 'Website',
    'summary': 'Promote question(s)/answers to documentation',
    'description': """
This module allows to push/promote functional documentation based on frequently asked question(s) and with their pertinent answer(s).
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

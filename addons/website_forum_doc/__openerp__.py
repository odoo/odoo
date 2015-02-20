# -*- coding: utf-8 -*-

{
    'name': 'Documentation',
    'category': 'Website',
    'summary': 'Forum, Documentation',
    'version': '1.0',
    'description': """
Documentation based on question and pertinent answers of Forum
        """,
    'author': 'Odoo S.A.',
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

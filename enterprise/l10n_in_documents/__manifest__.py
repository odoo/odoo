# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'India - Documents',
    'version': '1.0',
    'description': """
Demo Documents for India
========================
This is help to show case the documents OCR for India.
    """,
    'category': 'Productivity/Documents',
    'depends': ['l10n_in', 'documents'],
    'demo': [
        'demo/documents_document_demo.xml',
    ],
    'auto_install': ['l10n_in', 'documents'],
    'installable': True,
    'license': 'OEEL-1',
}

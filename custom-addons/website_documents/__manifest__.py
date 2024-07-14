# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Website Documents',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'sequence': 8010,
    'summary': 'Choose the website on which documents/folder are shared',
    'website': 'https://www.odoo.com/app/documents',
    'description': """
When sharing documents/folder, the domain of the shared URL can be chosen by selecting a target website.
""",
    'depends': ['documents', 'website'],
    'data': [
        'views/documents_share_views.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

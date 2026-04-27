# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Contracts',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Store employee contracts in the Document app',
    'description': """
Employee contracts files will be automatically integrated to the Document app.
""",
    'website': ' ',
    'depends': ['documents_hr', 'hr_contract'],
    'data': [
        'data/documents_tag_data.xml',
        'data/res_company_data.xml',
        'views/documents_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

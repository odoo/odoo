# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Digest Enterprise',
    'description': """
Enterprise digest data
    """,
    'category': 'Hidden',
    'version': '1.0',
    'depends': ['web_enterprise', 'digest'],
    'data': [
        'data/digest_data.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}

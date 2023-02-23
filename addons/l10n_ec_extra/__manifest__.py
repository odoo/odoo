# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Extra functions for EC',
    'version': '1.0',
    'category': 'Tools',
    'description': '''
        Extended functions for EC.
    ''',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD CIA. LTDA.',
    'website': 'http://www.trescloud.com',
    'license': 'OEEL-1',
    'depends': [
        'l10n_ec'
    ],
    'data': [
        'views/res_partner_view.xml'
    ],
    'installable': True,
    'application': True,
}

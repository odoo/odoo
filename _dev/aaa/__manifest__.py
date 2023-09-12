# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "AAA",
    'version': '1.0',
    'depends': ["base"],
    'author': "Author Name",
    'category': 'Sales/CRM',
    'description': """  AAA Description text  """,
    'data': [
        # 'security/crm_security.xml',
        'security/ir.model.access.csv',

        'views/aaa_views.xml'
    ],
    # data files containing optionally loaded demonstration data
    'demo': [
        # 'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}

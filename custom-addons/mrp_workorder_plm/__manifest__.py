# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'PLM for workorder',
    'version': '1.0',
    'category': 'Manufacturing/Product Lifecycle Management (PLM)',
    'description': """
PLM for workorder.
=================================================
    """,
    'summary': 'PLM for workorder',
    'depends': [
        'mrp_workorder',
        'mrp_plm',
    ],
    'data': [
        'views/mrp_eco_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

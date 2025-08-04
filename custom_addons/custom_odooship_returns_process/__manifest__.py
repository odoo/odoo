# Part of Odoo. See LICENSE file for full copyright and licensing details.
# -*- coding: utf-8 -*-
{
    'name': 'Shiperoo Custom Returns Process',
    'version': '17.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Shiperoo Returns Process',
    'description': """Returns/Scrap process""",
    'author': 'Drishti Joshi',
    'company': 'Shiperoo',
    'depends': ['stock', 'base', 'sale','custom_odooship_decanting_process',
                'custom_odooship_outbound_process'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_inherit_views.xml',
        'views/grade_message_configuration_views.xml',
        'wizard/custom_returns_wizard_view.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': True,
    'license': 'LGPL-3',
}


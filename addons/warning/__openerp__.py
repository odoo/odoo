# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Warning Messages and Alerts',
    'version': '1.0',
    'category': 'Tools',
    'description': """
Module to trigger warnings in OpenERP objects.
==============================================

Warning messages can be displayed for objects like sale order, purchase order,
picking and invoice. The message is triggered by the form's onchange event.
    """,
    'depends': ['base', 'sale_stock', 'purchase'],
    'data': ['warning_view.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

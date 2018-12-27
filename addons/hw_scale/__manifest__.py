# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Weighing Scale Hardware Driver',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Hardware Driver for Weighing Scales',
    'website': 'https://www.odoo.com/page/point-of-sale-hardware',
    'description': """
Weighing Scale Hardware Driver
================================

This module allows the point of sale to connect to a scale using a USB HSM Serial Scale Interface,
such as the Mettler Toledo Ariva.

""",
    'depends': ['hw_proxy'],
    'external_dependencies': {'python': ['serial']},
    'installable': False,
}

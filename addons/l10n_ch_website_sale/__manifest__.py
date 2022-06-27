# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Main contributor: Nicolas Bessi. Camptocamp SA
# Financial contributors: Hasa SA, Open Net SA,
#                         Prisme Solutions Informatique SA, Quod SA
# Translation contributors: brain-tec AG, Agile Business Group
{
    'name': "Switzerland - Website Sale",
    'description': """
Swiss localization
==================

Bridge module with l10n_ch localisation module and website_sale. 

This module modify the behaviour of the website_sale when it generate the reference payement. This allows the reference to be 
QR-Bill friendly. 

    """,
    'version': '1.0',
    'depends': ['l10n_ch', 'sale_management'],
    'license': 'LGPL-3',
    'auto_install': True,
}

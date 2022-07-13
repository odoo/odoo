# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (c) 2019 - Blanco Martín & Asociados. https://www.bmya.cl
{
    'name': 'Chile - Accounting POS',
    'version': "3.0",
    'description': """
Chilean accounting chart and tax localization for POS.
Plan contable chileno e impuestos de acuerdo a disposiciones vigentes.
    """,
    'author': 'Blanco Martín & Asociados',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/accounting/fiscal_localizations/localizations/chile.html',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'l10n_cl',
        'point_of_sale'
        ],
    'assets': {
        'point_of_sale.assets': [
            'l10n_cl_pos/static/src/js/**/*.js',
        ],
        'web.assets_qweb': [
            'l10n_cl_pos/static/src/xml/**/*',
        ],
    },
    'license': 'LGPL-3',
}
    

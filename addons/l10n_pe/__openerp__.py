# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Cubic ERP - Teradata SAC. (http://cubicerp.com).

{
    'name': 'Peru - Accounting',
    'version': '1.0',
    'description': """
Peruvian accounting chart and tax localization. According the PCGE 2010.
========================================================================

Plan contable peruano e impuestos de acuerdo a disposiciones vigentes de la
SUNAT 2011 (PCGE 2010).

    """,
    'author': ['Cubic ERP'],
    'website': 'http://cubicERP.com',
    'category': 'Localization/Account Charts',
    'depends': ['account'],
    'data':[
        'l10n_pe_chart.xml',
        'account_tax.xml',
        'account_chart_template.yml',
    ],
    'demo': [],
    'active': False,
    'installable': True,
}

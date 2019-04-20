# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Peru - Accounting',
    "version": "2.0",
    'summary': "PCGE Simplified",
    'category': 'Localization',
    'description': """
Minimal set of accounts to start to work in Perú.
=================================================

The usage of this CoA must refer to the official documentation on MEF.

https://www.mef.gob.pe/contenidos/conta_publ/documentac/VERSION_MODIFICADA_PCG_EMPRESARIAL.pdf 
    """,
    'depends': ['account'],
    'author': ['Vauxoo, Odoo'],
    'data': [
        'data/account_types.xml',
        'data/l10n_pe_chart_data.xml',
        'data/account.group.csv',
        'data/account.account.template.csv',
        'data/l10n_pe_chart_post_data.xml',
        'data/account_tax_data.xml',
        'data/account_chart_template_data.xml',
    ],
}

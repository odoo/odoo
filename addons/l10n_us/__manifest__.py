# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'United States - Localizations',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['us'],
    'version': '1.1',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
    """,
    'depends': ['base'],
    'data': [
        'data/res_company_data.xml',
        'views/res_partner_bank_views.xml'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Panama - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pa'],
    'description': """
Panamenian accounting chart and tax localization.

Plan contable panameño e impuestos de acuerdo a disposiciones vigentes

Con la Colaboración de
- AHMNET CORP http://www.ahmnet.com

    """,
    'author': 'Cubic ERP',
    'category': 'Accounting/Localizations/Account Charts',
    'depends': [
        'account',
        'base_address_extended',
        'l10n_latam_invoice_document',
    ],
    'auto_install': ['account'],
    'data': [
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
        'data/res_country_data.xml',
        'data/l10n_latam.document.type.csv',
        'data/res.city.csv',
        'data/l10n_pa.res.city.corregimiento.csv',
        'security/ir.access.csv',
    ],
    'demo': [
        'demo/demo_partner.xml',
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

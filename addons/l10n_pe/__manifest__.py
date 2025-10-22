# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Peru - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['pe'],
    'version': '3.1',
    'category': 'Accounting/Localizations/Account Charts',
    'author': 'Vauxoo, Odoo S.A.',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/peru.html',
    'license': 'LGPL-3',
    'depends': [
        'base_vat',
        'base_address_extended',
        'l10n_latam_base',
        'l10n_latam_invoice_document',
        'account_debit_note',
        'account',
    ],
    'auto_install': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_tax_view.xml',
        'views/portal_address_templates.xml',
        'views/res_bank_view.xml',
        'data/l10n_latam_document_type_data.xml',
        'data/res.city.csv',
        'data/l10n_pe.res.city.district.csv',
        'data/res_country_data.xml',
        'data/l10n_latam_identification_type_data.xml',
        'data/res.bank.csv',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_pe/static/src/interactions/**/*',
        ],
    },
    'demo': [
        'demo/demo_company.xml',
        'demo/demo_partner.xml',
    ],
}

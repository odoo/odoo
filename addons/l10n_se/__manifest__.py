# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Sweden - Accounting',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'icon': '/account/static/description/l10n.png',
    'countries': ['se'],
    'version': '1.3',
    'author': 'XCLUDE, Odoo S.A.',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """
Swedish Accounting
------------------

This is the base module to manage the accounting chart for Sweden in Odoo.
It also includes the invoice OCR payment reference handling.
    """,
    'depends': [
        'account',
        'account_edi_ubl_cii',
    ],
    'auto_install': ['account'],
    'data': [
        'security/ir.access.csv',
        'data/account.account.tag.csv',
        'data/l10n_se.sni.csv',
        'data/account_tax_report_data.xml',
        'data/res_country_data.xml',
        'views/partner_view.xml',
        'views/account_journal_view.xml',
        'views/l10n_se_sru_mapping_views.xml',
        'views/l10n_se_sni_views.xml',
        'views/res_config_settings_views.xml',
        'views/report_invoice_templates.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

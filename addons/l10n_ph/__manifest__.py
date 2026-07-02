# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Philippines - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ph'],
    'summary': "This is the module to manage the accounting chart for The Philippines.",
    'category': 'Accounting/Localizations/Account Charts',
    'version': '1.1',
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/philippines.html',
    'depends': [
        'account',
        'base_vat',
        'l10n_account_withholding_tax',
    ],
    'auto_install': ['account'],
    'data': [
        'data/account_tax_report_data.xml',
        'security/security.xml',
        'wizard/l10n_ph_discount_privilege_wizard_views.xml',
        'views/res_config_settings_views.xml',
        'views/l10n_ph_discount_privilege_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/report_disbursement_voucher_template.xml',
        'views/report_disbursement_voucher_internal_template.xml',
        'views/account_report.xml',
        'views/report_templates.xml',
        'data/menuitem_data.xml',
        'security/ir.access.csv'
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'license': 'LGPL-3',
}

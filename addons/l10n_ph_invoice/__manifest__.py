# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Philippines - Discount Privileges on Invoice',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ph'],
    'summary': "Apply Philippine SC/PWD discount privileges on customer invoices and credit notes.",
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/philippines.html',
    'depends': [
        'l10n_ph',
    ],
    'data': [
        'security/ir.access.csv',
        'wizard/l10n_ph_discount_privilege_wizard_views.xml',
        'views/l10n_ph_discount_privilege_views.xml',
        'views/account_move_views.xml',
        'data/menuitem_data.xml',
    ],
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Philippines - Discount Privileges on Sale Orders',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ph'],
    'summary': "Apply Philippine SC/PWD discount privileges on quotations and sale orders.",
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/philippines.html',
    'depends': [
        'l10n_ph_invoice',
        'sale',
    ],
    'data': [
        'security/ir.access.csv',
        'views/sale_order_views.xml',
    ],
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Japan - Purchase Document Layout',
    'countries': ['jp'],
    'category': 'Accounting/Localizations',
    'author': 'Odoo S.A.',
    'depends': [
        'l10n_jp',
        'purchase',
    ],
    'data': [
        'report/purchase_order_templates.xml',
        'report/purchase_quotation_templates.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Mandate invoicing for Colombia',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'Colombian EDI Mandate Invoicing extension',
    'author': 'Odoo Sa',
    'depends': ['l10n_co_dian'],
    'auto_install': True,
    'data': [
        'views/account_move_views.xml',
        'views/product_template_views.xml',
        'views/ubl_20_templates.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}

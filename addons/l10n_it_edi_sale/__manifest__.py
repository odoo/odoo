{
    'name': 'Italy - Sale E-invoicing',
    'version': '1.0',
    'depends': [
        'l10n_it_edi',
        'sale',
    ],
    'description': 'Sale modifications for Italy E-invoicing',
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/italy.html',
    'data': [
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

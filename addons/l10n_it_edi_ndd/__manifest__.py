{
    'name': 'Italy - E-invoicing - Additional module to support the debit notes (nota di debito - NDD)',
    'countries': ['it'],
    'version': '1.0',
    'depends': [
        'l10n_it_edi',
    ],
    'auto_install': True,
    'description': """
Additional module to support the debit notes (nota di debito - NDD) by adding payment method and document types
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'https://www.odoo.com/documentation/master/applications/finance/fiscal_localizations/italy.html',
    'data': [
        'views/account_move_views.xml',
        'views/account_payment_method.xml',
        'views/l10n_it_document_type.xml',
        'data/l10n_it.document.type.csv',
        'security/ir.model.access.csv',
    ],
    'license': 'LGPL-3',
}

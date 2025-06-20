{
    'name': 'Türkiye - Nilvera E-Invoice Extended',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
For sending and receiving more types of electronic invoices to Nilvera.
    """,
    'depends': ['l10n_tr_nilvera_einvoice', 'contacts'],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_tr.res.tax.office.csv',
        'data/l10n_tr_account_tax_code_data.xml',
        'data/res_partner_data.xml',
        'data/account_incoterms_data.xml',
        'data/ubl_tr_templates.xml',
        'views/l10n_tr_account_tax_code_views.xml',
        'views/l10n_tr_res_tax_office_views.xml',
        'views/res_partner_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/product_views.xml'
    ],
    'license': 'LGPL-3',
}

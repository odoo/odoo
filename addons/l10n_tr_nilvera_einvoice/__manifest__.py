{
    'name': 'Türkiye - Nilvera E-Invoice',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
For sending and receiving electronic invoices to Nilvera.
    """,
    'depends': ['l10n_tr_nilvera', 'account_edi_ubl_cii'],
    'data': [
        'data/cron.xml',
        'data/res_partner_category_data.xml',
        'views/account_move_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
    ],
    'auto_install': ['l10n_tr_nilvera'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

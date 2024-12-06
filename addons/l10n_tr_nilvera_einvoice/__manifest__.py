{
    'name': 'Türkiye - Nilvera E-Invoice',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['l10n_tr_nilvera', 'account_edi_ubl_cii'],
    'data': [
        'data/cron.xml',
        'views/account_journal_dashboard_views.xml',
        'views/account_move_views.xml',
        'wizard/account_move_send_views.xml',
    ],
    'auto_install': ['l10n_tr_nilvera'],
    'license': 'OEEL-1',
}

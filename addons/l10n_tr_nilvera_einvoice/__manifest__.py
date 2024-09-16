# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Turkey - Nilvera E-Invoice',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'depends': ['l10n_tr_nilvera', 'account_edi_ubl_cii'],
    'data': [
        'data/cron.xml',
        'wizard/account_move_send_views.xml',
    ],
    'license': 'OEEL-1',
}

{
    'name': 'Türkiye - Nilvera E-Invoice Commercial',
    'category': 'Accounting/Accounting',
    'description': """
This module extends the Nilvera integration with the Commercial invoice scenario required for Turkish e-Invoicing compliance.

Features include:

- Support for invoice scenario: Commercial
- Ability to accept or reject commercial bills and synchronize customer responses.
    """,
    'depends': ['l10n_tr_nilvera_einvoice'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/account_move_views.xml',
        'wizards/l10n_tr_nilvera_einvoice_ticarifatura_response_wizard_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

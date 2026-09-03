{
    'name': 'Türkiye - Nilvera E-Invoice Commercial and Return',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
This module extends the Nilvera integration with additional invoice scenarios and types required for Turkish e-Invoicing compliance.

Features include:

- Support for invoice scenario: Commercial
- Support for invoice types: Return and Withholding Return
- Sending credit notes to Nilvera as return invoices linked to the original invoice
- Ability to accept or reject commercial bills and synchronize customer responses.
    """,
    'depends': ['l10n_tr_nilvera_einvoice_extended'],
    'data': [
        'security/ir.model.access.csv',
        'data/cron.xml',
        'views/account_move_views.xml',
        'wizards/l10n_tr_nilvera_einvoice_ticarifatura_response_wizard_views.xml',
    ],
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

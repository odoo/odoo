# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "Latam Document",
    "version": "12.0.1.0.0",
    "author": "ADHOC SA",
    "category": "Localization",
    "depends": [
        "account",
    ],
    "data": [
        'views/account_journal_view.xml',
        'views/account_move_line_view.xml',
        'views/account_move_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'views/account_invoice_view.xml',
        'views/report_invoice.xml',
        'views/ir_sequence_view.xml',
        'report/invoice_report_view.xml',
        'wizards/account_invoice_refund_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}

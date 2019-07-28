# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "LATAM Document",
    "version": "13.0.1.0.0",
    "author": "ADHOC SA",
    "category": "Localization",
    'description': """
LATAM Document
==============

This module is intended to be extended by localizations (like Argentina and
Chile) in order to manage the document types that need to be reported to the
government required by this countries.

In order to do that we add a new model named l10n_ar_document_type and we create
links between this new model and another Odoo's models.
""",
    "depends": [
        "account",
    ],
    "data": [
        'views/account_journal_view.xml',
        'views/account_move_line_view.xml',
        'views/account_move_view.xml',
        'views/l10n_latam_document_type_view.xml',
        'views/report_invoice.xml',
        'views/ir_sequence_view.xml',
        'report/invoice_report_view.xml',
        'wizards/account_move_reversal_view.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}

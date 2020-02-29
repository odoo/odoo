# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "LATAM Document",
    "version": "1.0",
    "author": "ADHOC SA",
    "category": "Localization",
    "summary": "LATAM Document Types",
    'description': """
Functional
----------

In some Latinamerica countries, including Argentina and Chile, some accounting transactions like invoices and vendor bills are classified by a document types defined by the government fiscal authorities (In Argentina case AFIP, Chile case SII).

This module is intended to be extended by localizations in order to manage these document types and is an essential information that needs to be displayed in the printed reports and that needs to be easily identified, within the set of invoices as well of account moves.

Each document type have their own rules and sequence number, this last one is integrated with the invoice number and journal sequence in order to be easy for the localization user. In order to support or not this document types a Journal has a new option that lets to use document or not.

Technical
---------

If your localization needs this logic will then need to add this module as dependency and in your localization module extend:

* extend company's _localization_use_documents() method.
* create the data of the document types that exists for the specific country. The document type has a country field

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

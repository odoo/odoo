# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Accounting Features",
    "version": "19.0.1.8.0",
    "author": "OD19",
    "category": "Accounting/Localizations",
    "summary": "Cancel reason wizard, payer/payee, BOT URL, prepayment due date, "
    "payment number, WHT base computed, AP bill-first gate "
    "(require Vendor Bill before payment), unique supplier reference on "
    "vendor bills, period clearing wizard, VAT/WHT/Suspense-Intercompany "
    "clearing wizards with settlement entries, central reconciliation "
    "helpers, and OCA journal sequence + lock date controls (the OCA "
    "reconcile UI is wired in by the bridge module "
    "od19_accounting_reconcile_ui)",
    "description": """
OD19 Accounting Features
========================

Provides several accounting features for the Thai localization:

* Cancel reason wizard on invoices (all move types).
* Payer / Payee partner fields on prepayments.
* BOT (Revenue Department) URL configuration with a smart link on invoices.
* Prepayment actual due date (invoice date + 30 days).
* Payment number displayed on vendor bills.
* Unique supplier reference (vendor tax invoice number) per vendor and
  company on vendor bills/refunds, to prevent double-booking.
* Withholding tax (WHT) base amount computed from selected invoices.
* Central reconciliation helpers (``_od19_reconcile_account_lines`` /
  ``_od19_reconcile_move_lines``) reused by every custom business flow.
* Period Clearing wizard (กระทบยอดปิดงวด) to clear the open journal items
  of the control accounts (AR/AP, bank, suspense, VAT/WHT) of a period.
* VAT Clearing wizard (ภ.พ.30) that nets output/input VAT of a period,
  posts the settlement entry to the VAT payable (or refundable) account
  and reconciles the VAT control accounts.
* WHT Clearing wizard that consolidates the withholding tax payable of a
  period into the WHT-to-remit account (optional settlement entry) and
  reconciles the WHT control accounts.
* Suspense / Intercompany Clearing wizard that reconciles the suspense
  and intercompany due-to/due-from control accounts (reconcile only).
* OCA journal entry numbering from sequence (year reset, no gaps) via
  ``account_move_name_sequence``.
* OCA lock date update wizard (account adviser can set locking dates)
  via ``account_lock_date_update``.

The OCA manual reconciliation UI (``account_reconcile_oca``) is no longer a
hard dependency of this module. It is wired in by the bridge module
``od19_accounting_reconcile_ui`` (auto-install), which keeps this core
decoupled from the AGPL addon while still providing the same screen on a
standard OD19 CE deployment.

The advisory WHT Certificate PDFs that used to be printed from
``account.payment`` were retired in favour of the GL-accurate
certificate printed from the OCA model ``withholding.tax.cert``
(see module ``od19_thai_tax_reports``).
    """,
    "depends": [
        "account",
        "account_payment",
        "mail",
        "l10n_th_account_tax",
        "account_move_name_sequence",
        "account_lock_date_update",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/account_move_cancel_reason_views.xml",
        "wizards/account_period_clear_views.xml",
        "wizards/account_clearing_views.xml",
        "views/res_config_settings_views.xml",
        "views/account_move_views.xml",
        "views/account_payment_views.xml",
        "report/billing_note_report.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_accounting_features/static/description/icon.svg",
}

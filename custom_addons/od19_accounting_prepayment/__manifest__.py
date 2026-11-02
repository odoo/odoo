# Copyright 2026 OD19
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
{
    "name": "OD19 Accounting - Prepare Payment (Billing)",
    "version": "19.0.1.0.0",
    "category": "Accounting/Payments",
    "summary": "OD15 \"Prepare Payments\" (dtr.account.prepayment) rebased on the "
    "OCA account_billing vendor flow: menu, smart buttons and a dedicated "
    "access group.",
    "description": """
OD19 Accounting - Prepare Payment (Billing)
===========================================

The legacy Odoo 15 document ``dtr.account.prepayment`` ("Prepare Payments",
under Payables) was already re-based on the OCA ``account_billing`` model
(``bill_type='in_invoice'``) during the Odoo 19 port - see
``od19_reporting_jasper`` wizard ``prepayment.condition.report`` which maps
``dtr_account_prepayment`` to ``account_billing``.  This module therefore does
**not** add a second, duplicate model.  It provides the OD15 user experience on
top of the existing OCA document:

* Renames the vendor "Billing" menu to **Prepare Payments** (Payables) and the
  unrelated ``account.payment`` menu to **Payment Vouchers**, removing the
  naming clash between the two.
* Adds a smart button (**Prepare Payments**) on the Vendor Bill, the Purchase
  Order and the Payment, counting the billing documents each one belongs to.
* Adds the **Prepare Payments** access group that gates the menu.

Depends on ``account_billing`` (OCA) which supplies the ``account.billing``
document and the ``billing_ids`` link on ``account.move``.
    """,
    "author": "OD19",
    "license": "LGPL-3",
    "depends": [
        "account",
        "account_billing",
        "purchase",
    ],
    "data": [
        "security/od19_prepayment_security.xml",
        "views/account_billing_views.xml",
        "views/integration_views.xml",
    ],
    "installable": True,
    "application": False,
    "icon": "/od19_accounting_prepayment/static/description/icon.svg",
}

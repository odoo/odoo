{
    "name": "Vendor Bill Document Extraction",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "summary": "Read a vendor bill's own document with extract",
    "description": """
Vendor Bill Document Extraction
===============================

Puts ``mixin.extract`` on ``account.move``, replacing
``account_invoice_extract``'s reading of a vendor bill.

What the cascade adds over a single service is order. A Mexican vendor bill
arrives with a CFDI: an XML its issuer stamped and the SAT certified. Copying a
total out of that is neither a reading nor a purchase, and the cascade reaches
it first, so a document that carries its own data never reaches something that
charges per page. Only a bill with no structured source of its own gets that
far.

It also keeps what a single service does not: which strategy produced each
value, which required fields nobody could read, and what a person changed
afterwards.

Header fields only
------------------
A date, a reference, a supplier matched on the tax identifier the document
states, a currency it names -- and each written only into emptiness, never over
something a person put there. A supplier is matched, never created: a vendor
invented from a misread tax number is a partner nobody asked for, sitting in the
ledger under a name that looks deliberate.

Lines are never posted by an extraction. A line carries an account, taxes and a
product, and the bill's total is computed from those -- so a wrong line is a
wrong balance rather than a wrong label.

They are offered instead. "Review read lines" opens a screen listing what the
document said, with which strategy said it, and totals the accepted lines
against the total read from the document so the two can be seen disagreeing. A
line is added only once a person has accepted it, and a line they edited before
accepting is recorded as a correction, because a person disagreeing with a
reader is the most useful thing this system learns.

Replaces, rather than joining
-----------------------------
Both mixins declare ``extract_state``, so a model cannot carry both. Odoo's
``account_invoice_extract`` is marked uninstallable in this fork rather than
merely uninstalled, because it and its glue module ``account_extract`` are both
``auto_install`` and would return on the next module update.
    """,
    "author": "AgroMarin",
    "website": "https://agromarin.com",
    "license": "LGPL-3",
    "depends": [
        "account",
        "extract",
    ],
    "data": [
        "security/ir.access.csv",
        "wizards/extract_line_wizard_views.xml",
        "views/account_move_views.xml",
    ],
}

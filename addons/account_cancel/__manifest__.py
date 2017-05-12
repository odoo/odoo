# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Cancel Journal Entries',
    'version': '1.1',
    'category': 'Accounting',
    'description': """
Allows canceling accounting entries.
====================================

This module adds 'Allow Canceling Entries' field on form view of account journal.
If set to true it allows user to cancel entries & invoices.

This is a very minor feature, packaged as a module.

Although it is called "cancel", it operates more like "unpost" or "undo post"

It has two functions...

1) Enable a setting on general ledger journal types: "Allow cancelling entries"

2) Make the "Cancel" button on each journal active.

When cancelled, the journal reverts to unposted, whereupon it can be edited and reposted or deleted.

Also operates on bank statements, customer invoices, supplier invoices and account payments.

It works correctly in v10.

It is most likely an external module to prevent this feature being easily enabled in default systems, as it has audit implications. If a journal, invoice, payment or bank statement has been posted and completed, and can later be undone, it potentially removes evidence that a transaction has occured. No audit log of cancellations is created.

Conversly, it is also a useful way to fix genuine mistakes, without sometimes ugly and difficult to follow reversals and reposts.

A brief post by Siraz with screen shots is here. http://openerpfaqs.com/how-to-cancel-journal-entries-in-odoo-financial-accounting/

This feature is packaged in the core Odoo repository under odoo/addons/account_cancel, and no external components are required.

The underlying cancel logic is included in core, not in this module.
    """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account'],
    'data': ['views/account_views.xml'],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

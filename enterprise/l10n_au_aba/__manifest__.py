# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Based on the module developped by Richard de Meester, from Willdoo IT
{
    'name': "ABA Credit Transfer",
    'summary': """Export payments as ABA Credit Transfer files""",
    'description': """
ABA Credit Transfer
===================

This module allows the generation of payment batches as ABA (Australian
Bankers Association) text files.  The generated 'aba' file can be uploaded
to many Australian banks.

Setup
-----

- *Account > Configuration > invoicing > Journals*

    If needed, create new journal or choose an existing journal with **Type**
    set to *“Bank”*.

    On **Advanced Settings**, ensure ABA Credit Transfer is ticked.

    On the **Bank Account** tab, enter the **Account Number**.

    On the same tab, ensure the ABA transfer information is set up.

    **BSB** - Required, 6 digits, and will be auto formatted.

    **Financial Institution Code** - Required (provided by bank or can be found
    on Google).  It is three uppercase 3 characters.

    **Supplying User Name** - Some banks allow this to be freeform, some banks
    may reject the ABA file if the Supplying User Name is not as expected.  It
    cannot be longer than 26 characters.

    **APCA Identification Number** - User Identification number is bank
    allocated.  It is 6 digits.

    **Include Self Balancing Transaction** - Some institutions require that the
    last be a self balancing transaction which is used as a verification.

- *Accounting > Configuration > Payments > Bank Accounts*

    Account will show up in list as the journal name.

    Editing will show the **Account Number**.  This is important as it is used by
    the ABA process.

    **Bank** is optional.

- *Contacts > Configuration > Bank Accounts > Bank Accounts*

    Paying account will show up in list as the account number.

    **Account Holder Name** - Can be entered here, if Required.  Generally not
    validated by the banks on ABA file transfers, but may show up on the payee
    bank statement against the payment.

- Vendor bank accounts can be set up in the same place, however, it is
  generally easier to set them up from the partner from for the Vendor.

- *Accounting > Vendors > Vendors*

    On **Accounting** tab, click on *"View accounts detail"* from where a
    vendor bank account can be created or edited.

    **Account Number** - Required, must be less than 9 digits.

    **BSB** - Required, 6 digits, and will be auto formatted.

    **Account Holder Name** - Optional.

Use
---

- Create a vendor payment in the normal way.

    Ensure the **Vendor** is one with a valid ABA payment account.

    Choose the correct **Payment Journal** which is set for ABA payments.

    Select **ABA Credit Transfer** radio button.

    If the vendor has multiple bank account, you may need to select the
    correct **Recipient Bank Account**.  Or if paying a vendor bill, it may
    need the correct bank account associated with it.

    Enter payment amount, etc.

- *Vendors > Payments*

    After payment(s) are confirmed, they will show up in the payments list.

    Using filters, or sorting, select the payments to be included.  Under
    *Actions* choose *Create batch payment*.

- *Vendors > Batch Payments*

    When validating a batch payment, the ABA file will be generated.  It can
    be regenerated.  This file can then be uploaded to the bank.
""",
    'category': 'Accounting/Localizations/EDI',
    'version': '1.0',
    'depends': ['account_batch_payment', 'l10n_au'],
    'data': [
        'data/aba_data.xml',
        'views/account_journal_views.xml',
        'views/account_journal_dashboard_views.xml',
        'views/account_payment_views.xml',
        'views/res_partner.xml',
    ],
    'installable': True,
    'auto_install': ['l10n_au'],
    'license': 'OEEL-1',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "SEPA Direct Debit",

    'summary': "Collect payments from your customers through SEPA direct debit.",

    'description': """
This module enables the generation of SEPA Direct Debit (SDD)-compliant XML files (consistent
with pain.008.001.02 specification) to send to your bank in order to
collect a set of payments.

To be elligible for this payment method, a customer must have first
returned a mandate to the company, giving his consent to use direct debit.
This consent must have been encoded as a 'customer mandate' into Odoo.

You also need to meet the following requirements in order to properly
generate a SDD file:
- Your company account must be set to a valid IBAN number
- Your company must have been given a creditor identifier (this can be done in the 'settings' menu of the accounting module)
- Your company must have defined a journal to receive SDD payments (again, in 'settings' of accounting module)
- Every customer for which you generate a payment must have a valid IBAN account number.

Odoo will let you know if any of these requirements are not satisfied.

Any invoice that gets validated for a customer with a mandate will be
automatically set in 'paid' state, and a payment will be generated. An
option in the dashboard will then allow you to view all the payments generated
via SDD and to generate a XML collection file for them, grouping them as
you see fit.

A dedicated 'SEPA Direct Debit' payment method is also available for
open invoices, when selecting a bank account in the 'register payment' wizard.
Use it to generate a SDD payment for the invoices if you added a mandate
for its owner after its validation. You will see an error message if you
try to use this method on an invoice for whose payment no mandate can be used.
    """,

    'category': 'Accounting/Accounting',

    'depends': ['base_iban', 'account_batch_payment', 'account'],

    'data': [
        'security/account_sepa_direct_debit_security.xml',
        'security/ir.model.access.csv',
        'report/empty_mandate_report.xml',
        'data/account_data.xml',
        'data/sdd_payment_method.xml',
        'data/sdd_mandate_state_cron.xml',
        'views/sdd_mandate_views.xml',
        'views/account_payment_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_view.xml',
        'views/account_batch_payment_views.xml',
        'views/account_move_view.xml',
        'views/account_journal_views.xml',
    ],
    'license': 'OEEL-1',
}

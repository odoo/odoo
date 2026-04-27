# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "SEPA Direct Debit",

    'summary': "Collect payments from your customers through SEPA direct debit.",

    'description': """
This module enables the generation of SEPA Direct Debit (SDD)-compliant XML files (consistent
with pain.008.001.02 specification) to send to your bank in order to
collect a set of payments.

To be eligible for this payment method, a customer must have first
returned a mandate to the company, giving their consent to use direct debit.
This consent must have been encoded as a 'customer mandate' in Odoo.

You also need to meet the following requirements in order to properly
generate an SDD file:
- Your company account must be set to a valid IBAN number
- Your company must have been given a creditor identifier (this can be done in Settings - General Settings - Accounting section)
- Your company must have defined a journal to receive SDD payments (again, in 'settings' of accounting module)
- Every customer for whom you generate a payment must have a valid IBAN account number.

Odoo will let you know if any of these requirements are not satisfied.

To register a payment for open invoices, you can use the dedicated
'SEPA Direct Debit' option by selecting a bank account in the 'Register
Payment' wizard. An error message will appear if no valid mandate is
available for generating a payment on the selected invoice.
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
        'data/email_templates.xml',
        'views/sdd_mandate_views.xml',
        'views/account_payment_view.xml',
        'views/account_journal_dashboard_view.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_view.xml',
        'views/account_batch_payment_views.xml',
        'views/account_move_view.xml',
        'views/account_journal_views.xml',
        'wizard/account_payment_register_view.xml',
        'wizard/sdd_mandate_send_views.xml',
    ],
    'license': 'OEEL-1',
}

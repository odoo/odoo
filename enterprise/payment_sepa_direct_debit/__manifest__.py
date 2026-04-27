# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment Provider: Sepa Direct Debit",
    'version': '2.0',
    'category': 'Accounting/Accounting',
    'sequence': 350,
    'summary': "A payment provider for enabling Sepa Direct Debit in the EU.",
    'description': " ",  # Non-empty string to avoid loading the README file.
    'depends': ['account_sepa_direct_debit', 'account_payment', 'payment_custom'],
    'data': [
        'views/payment_provider_views.xml',
        'views/payment_sepa_direct_debit_templates.xml',

        'data/ir_cron.xml',
        'data/mail_template_data.xml',
        'data/payment_provider_data.xml',  # Depends on `inline_form`, `payment_method_sepa`.
    ],
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_sepa_direct_debit/static/src/js/payment_form.js',
        ],
    },
    'license': 'OEEL-1',
}

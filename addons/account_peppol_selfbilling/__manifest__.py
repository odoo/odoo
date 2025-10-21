# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Peppol Self Billing",
    'summary': "Send and receive self-billing invoices on PEPPOL",
    'category': 'Accounting/Accounting',
    'depends': ['account_peppol'],
    'data': [
        'views/account_move_views.xml',
        'views/account_journal_views.xml',
        'data/mail_template.xml',
        'data/report_invoice.xml',
    ],
    'license': 'LGPL-3',
    'auto_install': ['account_peppol'],
}

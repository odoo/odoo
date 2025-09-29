# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Peppol",
    'summary': "This module is used to send/receive documents with PEPPOL",
    'website': 'https://www.odoo.com/documentation/16.0/applications/finance/accounting/customer_invoices/electronic_invoicing.html#peppol',
    'description': """
- Register as a PEPPOL participant
- Send and receive documents via PEPPOL network in Peppol BIS Billing 3.0 format
    """,
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': [
        'account_edi_proxy_client',
        'account_edi_ubl_cii',
    ],
    'data': [
        'data/account_edi_data.xml',
        'data/cron.xml',
        'views/account_journal_dashboard_views.xml',
        'views/account_move_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/account_invoice_send_views.xml',
    ],
    'license': 'LGPL-3',
    'pre_init_hook': 'pre_init_hook',
}

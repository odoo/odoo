# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Test Discuss Full Enterprise',
    'category': 'Hidden',
    'summary': 'Test Suite for Discuss Enterprise',
    'auto_install': ['test_discuss_full', 'web_enterprise'],
    'depends': [
        'account_accountant',
        'account_invoice_extract',
        'approvals',
        'documents',
        'knowledge',
        'mail_enterprise',
        'sign',
        'test_discuss_full',
        'voip',
        'voip_onsip',
        'web_enterprise',
        'website_helpdesk_livechat',
        'web_studio',
        'whatsapp',
    ],
    'license': 'OEEL-1',
}

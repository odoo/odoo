#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name' : 'Email Gateway',
    'version' : '1.0',
    'depends' : ['mail'],
    'category': 'Extra Tools',
    'description': """
Retrieve incoming email on POP/IMAP servers.
============================================

Enter the parameters of your POP/IMAP account(s), and any incoming emails on
these accounts will be automatically downloaded into your OpenERP system. All
POP3/IMAP-compatible servers are supported, included those that require an
encrypted SSL/TLS connection.

This can be used to easily create email-based workflows for many email-enabled OpenERP documents, such as:
----------------------------------------------------------------------------------------------------------
    * CRM Leads/Opportunities
    * CRM Claims
    * Project Issues
    * Project Tasks
    * Human Resource Recruitments (Applicants)

Just install the relevant application, and you can assign any of these document
types (Leads, Project Issues) to your incoming email accounts. New emails will
automatically spawn new documents of the chosen type, so it's a snap to create a
mailbox-to-OpenERP integration. Even better: these documents directly act as mini
conversations synchronized by email. You can reply from within OpenERP, and the
answers will automatically be collected when they come back, and attached to the
same *conversation* document.

For more specific needs, you may also assign custom-defined actions
(technically: Server Actions) to be triggered for each incoming mail.
    """,
    'website': 'https://www.odoo.com/page/mailing',
    'data': [
        'fetchmail_data.xml',
        'fetchmail_view.xml',
        'security/ir.model.access.csv',
        'fetchmail_installer_view.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
}

{
    "name" : "Email Template for Open ERP",
    "version" : "0.7 RC",
    "author" : "Open ERP",
    "website" : "http://openerp.com",
    "category" : "Added functionality",
    "depends" : ['base'],
    "description": """
    Email Template is extraction of Power Email basically just to send the emails.
    """,
    "init_xml": ['email_template_scheduler_data.xml'],
    "update_xml": [
        'security/email_template_security.xml',
        'email_template_workflow.xml',
        'email_template_account_view.xml',
        'email_template_view.xml',
        'email_template_mailbox_view.xml',
        'wizard/email_template_send_wizard_view.xml',
    ],
    "installable": True,
    "active": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

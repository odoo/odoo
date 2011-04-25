# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2010-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

{
    "name" : "Email Template for OpenERP",
    "version" : "0.7 RC",
    "author" : "Openlabs",
    "website" : "http://openerp.com",
    "category" : "Tools",
    "depends" : ['mail'],
    "description": """
Email Template is extraction of Power Email basically just to send emails.
==========================================================================

You can define email accounts(server, port, mail format - HTML/Text/Both)
and email templates (resource, recipient, subject, body, attachments).

For each email template, you can have OpenERP generate a Wizard Action / Button
that will be related to the object. So if you choose to do marketing campaigns
for leads, the action will be added to the right side panel of the Lead form.
    """,
    "init_xml": [],
    "update_xml": [
        'wizard/email_template_preview_view.xml',
        'email_template_view.xml',
        'wizard/email_compose_message_view.xml',
        'security/ir.model.access.csv'
    ],
    "installable": True,
    "active": False,
    "certificate" : "00817073628967384349",
    'images': ['images/1_email_account.jpeg','images/2_email_template.jpeg','images/3_emails.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

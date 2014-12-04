# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2009 Sharoon Thomas
#    Copyright (C) 2010-Today OpenERP SA (<http://www.openerp.com>)
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
    'name' : 'Email Templates',
    'version' : '1.1',
    'author' : 'OpenERP SA',
    'website' : 'https://www.odoo.com/page/mailing',
    'category' : 'Marketing',
    'depends' : ['mail'],
    'description': """
Email Templating (simplified version of the original Power Email by Openlabs).
==============================================================================

Lets you design complete email templates related to any OpenERP document (Sale
Orders, Invoices and so on), including sender, recipient, subject, body (HTML and
Text). You may also automatically attach files to your templates, or print and
attach a report.

For advanced use, the templates may include dynamic attributes of the document
they are related to. For example, you may use the name of a Partner's country
when writing to them, also providing a safe default in case the attribute is
not defined. Each template contains a built-in assistant to help with the
inclusion of these dynamic values.

If you enable the option, a composition assistant will also appear in the sidebar
of the OpenERP documents to which the template applies (e.g. Invoices).
This serves as a quick way to send a new email based on the template, after
reviewing and adapting the contents, if needed.
This composition assistant will also turn into a mass mailing system when called
for multiple documents at once.

These email templates are also at the heart of the marketing campaign system
(see the ``marketing_campaign`` application), if you need to automate larger
campaigns on any OpenERP document.

    **Technical note:** only the templating system of the original Power Email by Openlabs was kept.
    """,
    'data': [
        'wizard/email_template_preview_view.xml',
        'email_template_view.xml',
        'res_partner_view.xml',
        'ir_actions_view.xml',
        'wizard/mail_compose_message_view.xml',
        'security/ir.model.access.csv'
    ],
    'demo': [],
    'installable': True,
    'auto_install': True,
    'images': ['images/1_email_account.jpeg','images/2_email_template.jpeg','images/3_emails.jpeg'],
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

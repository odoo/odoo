# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-Today OpenERP S.A. (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Social Network',
    'version': '1.0',
    'category':'Social Network',
    'sequence': 2,
    'summary': 'Discussions, Mailing Lists, News',
    'description': """
A business oriented Social Networking with a fully-integrated email 
and message management.
=====================================================================

The Social Networking module provides an unified social network
abstraction layer allowing applications to display a complete 
communication history on documents. It gives the users the possibility
to read and send messages and emails in an unified way.

It also provides a feeds page combined to a subscription mechanism, that 
allows to follow documents, and to be constantly updated about recent
news.
        
The main features of the module are:
    * a clean and renewed communication history for any OpenERP
      document that can act as a discussion topic,
    * a discussion mean on documents,
    * a subscription mechanism to be updated about new messages on 
      interesting documents,
    * an unified feeds page to see recent messages and activity 
      on followed documents,
    * user communication through the feeds page,
    * a threaded discussion design,
    * relies on the global outgoing mail server, an integrated email
      management system allowing to send emails with a configurable 
      scheduler-based processing engine
    * includes an extensible generic email composition assistant, that can turn
      into a mass-mailing assistant, and is capable of interpreting
      simple *placeholder expressions* that will be replaced with
      dynamic data when each email is actually sent
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'base_tools', 'base_setup'],
    'data': [
        'wizard/mail_compose_message_view.xml',
        'res_config_view.xml',
        'mail_message_view.xml',
        'mail_followers_view.xml',
        'mail_thread_view.xml',
        'mail_group_view.xml',
        'res_partner_view.xml',
        'data/mail_data.xml',
        'data/mail_group_data.xml',
        'security/mail_security.xml',
        'security/ir.model.access.csv',
        'mail_alias_view.xml',
        'res_users_view.xml',
    ],
    'demo': [
        'data/mail_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
    'certificate': '001056784984222247309',
    'images': [
        'images/customer_history.jpeg',
        'images/messages_form.jpeg',
        'images/messages_list.jpeg',
        'static/src/img/email_icong.png',
        'static/src/img/_al.png',
        'static/src/img/_pincky.png',
        'static/src/img/groupdefault.png',
        'static/src/img/attachment.png',
        'static/src/img/checklist.png',
        'static/src/img/formatting.png',
    ],
    'css': [
        'static/src/css/mail.css',
        'static/src/css/mail_group.css',
        'static/src/css/mail_compose_message.css',
    ],
    'js': [
        'static/lib/jquery.expander/jquery.expander.js',
        'static/src/js/mail.js',
        'static/src/js/mail_followers.js',
    ],
    'qweb': [
        'static/src/xml/mail.xml',
        'static/src/xml/mail_followers.xml',
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

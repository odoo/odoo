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
    'category': 'Social Network',
    'sequence': 2,
    'summary': 'Discussions, Mailing Lists, News',
    'description': """
Business oriented Social Networking
===================================
The Social Networking module provides a unified social network abstraction layer allowing applications to display a complete
communication history on documents with a fully-integrated email and message management system.

It enables the users to read and send messages as well as emails. It also provides a feeds page combined to a subscription mechanism that allows to follow documents and to be constantly updated about recent news.

Main Features
-------------
* Clean and renewed communication history for any OpenERP document that can act as a discussion topic
* Subscription mechanism to be updated about new messages on interesting documents
* Unified feeds page to see recent messages and activity on followed documents
* User communication through the feeds page
* Threaded discussion design on documents
* Relies on the global outgoing mail server - an integrated email management system - allowing to send emails with a configurable scheduler-based processing engine
* Includes an extensible generic email composition assistant, that can turn into a mass-mailing assistant and is capable of interpreting simple *placeholder expressions* that will be replaced with dynamic data when each email is actually sent.
    """,
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/enterprise-social-network',
    'depends': ['base', 'base_setup'],
    'data': [
        'wizard/invite_view.xml',
        'wizard/mail_compose_message_view.xml',
        'mail_message_subtype.xml',
        'res_config_view.xml',
        'mail_message_view.xml',
        'mail_mail_view.xml',
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
        'views/mail.xml',
    ],
    'demo': [
        'data/mail_demo.xml',
        'data/mail_group_demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'qweb': [
        'static/src/xml/mail.xml',
        'static/src/xml/mail_followers.xml',
        'static/src/xml/announcement.xml',
        'static/src/xml/suggestions.xml',
    ],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

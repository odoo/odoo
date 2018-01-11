# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
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
    'name': 'Website Mail',
    'category': 'Hidden',
    'summary': 'Website Module for Mail',
    'version': '0.1',
    'description': """Glue module holding mail improvements for website.""",
    'author': 'OpenERP SA',
    'depends': ['website', 'mail', 'email_template'],
    'data': [
        'views/snippets.xml',
        'views/website_mail.xml',
        'views/website_email_designer.xml',
        'views/email_template_view.xml',
        'data/mail_groups.xml',
        'security/website_mail.xml',
    ],
    'qweb': [
        'static/src/xml/website_mail.xml'
    ],
    'installable': True,
    'auto_install': True,
}

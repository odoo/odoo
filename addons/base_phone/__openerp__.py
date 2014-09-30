# -*- encoding: utf-8 -*-
##############################################################################
#
#    Base Phone module for OpenERP
#    Copyright (C) 2014 Alexis de Lattre <alexis@via.ecp.fr>
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
    'name': 'Base Phone',
    'version': '0.1',
    'category': 'Phone',
    'license': 'AGPL-3',
    'summary': 'Validate phone numbers',
    'description': """
Base Phone
==========

This module validate phone numbers using the *phonenumbers* Python library, which is a port of the library used in Android smartphones. For example, if your user is linked to a French company and you update the form view of a partner with a badly written French phone number such as '01-55-42-12-42', Odoo will automatically update the phone number to E.164 format '+33155421242' and display in the form view of the partner the readable equivalent '+33 1 55 42 12 42'.

This module also adds *tel:* links on phone numbers and *fax:* links on fax numbers. If you have a softphone or a client software on your PC that is associated with *tel:* links, the softphone should propose you to dial the phone number when you click on such a link.

This module also updates the format() function for reports and adds 2 arguments :

* *phone* : should be True for a phone number, False (default) otherwize.
* *phone_format* : it can have 3 possible values :
    * *international* (default) : the report will display '+33 1 55 42 12 42'
    * *national* : the report will display '01 55 42 12 42'
    * *e164* : the report will display '+33155421242'

For example, in the Sale Order report, to display the phone number of the Salesman, you can write :  o.user_id and o.user_id.phone and format(o.user_id.phone, phone=True, phone_format='national') or ''

This module is independant from the Asterisk connector.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com> for any help or question about this module.
""",
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['base', 'web'],
    'external_dependencies': {'python': ['phonenumbers']},
    'data': [
        'security/phone_security.xml',
        'security/ir.model.access.csv',
        'res_partner_view.xml',
        'res_company_view.xml',
        'res_users_view.xml',
        'wizard/reformat_all_phonenumbers_view.xml',
        'wizard/number_not_found_view.xml',
        'web_phone.xml',
        ],
    'qweb': ['static/src/xml/*.xml'],
    'demo': ['base_phone_demo.xml'],
    'images': [],
    'installable': True,
}

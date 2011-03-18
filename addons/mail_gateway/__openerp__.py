# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Email Gateway System',
    'version': '1.0',
    'category': 'Tools',
    'description': """
    The generic email gateway system allows to send and receive emails.
    ===================================================================

    * History of emails
    * Easy integration with any module""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': [
        "mail_gateway_view.xml",
        "res_partner_view.xml",
        'security/ir.model.access.csv'

    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '001056784984222247309',
    'images': ['images/customer_history.jpeg','images/messages_form.jpeg','images/messages_list.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

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
    'name': 'Automated Action Rules',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
This module allows to implement action rules for any object.
============================================================

Use automated actions to automatically trigger actions for various screens.

**Example:** A lead created by a specific user may be automatically set to a specific
sales team, or an opportunity which still has status pending after 14 days might
trigger an automatic reminder email.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'mail'],
    'data': [
        'base_action_rule_view.xml',
        'security/ir.model.access.csv',
        'base_action_rule_data.xml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '001017908446466333429',
    'images': ['images/base_action_rule1.jpeg','images/base_action_rule2.jpeg','images/base_action_rule3.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

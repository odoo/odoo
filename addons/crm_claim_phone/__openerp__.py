# -*- encoding: utf-8 -*-
##############################################################################
#
#    CRM Claim Phone module for Odoo/OpenERP
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
    'name': 'CRM Claim Phone',
    'version': '0.1',
    'category': 'Phone',
    'license': 'AGPL-3',
    'summary': 'Validate phone numbers in CRM Claims',
    'description': """
CRM Claims Phone
================

This module validate phone numbers in the CRM Claim module, just like the *base_phone* module valide phone numbers in the Partner form. Please refer to the description of the *base_phone* module for more information.

This module is independant from the Asterisk connector.

Please contact Alexis de Lattre from Akretion <alexis.delattre@akretion.com> for any help or question about this module.
""",
    'author': 'Akretion',
    'website': 'http://www.akretion.com/',
    'depends': ['base_phone', 'crm_claim'],
    'data': ['crm_claim_view.xml'],
    'images': [],
    'installable': True,
    'auto_install': True,
    'active': False,
}

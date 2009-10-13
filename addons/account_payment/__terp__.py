# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
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
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    "name": "Payment Management",
    "version": "1.1",
    "author": "Tiny",
    "category": "Generic Modules/Payment",
    "depends": ["account"],
    "init_xml": [],
    "description": """
    This module provide :
    * a more efficient way to manage invoice payment.
    * a basic mechanism to easily plug various automated payment.
    """,
    'author': 'Tiny',
    'depends': ['account'],
    'init_xml': [],
    'update_xml': [
        'security/account_payment_security.xml',
        'security/ir.model.access.csv',
        'payment_wizard.xml',
        'payment_view.xml',
        'payment_workflow.xml',
        'payment_sequence.xml',
        'account_invoice_view.xml',
        'payment_report.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0061703998541',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

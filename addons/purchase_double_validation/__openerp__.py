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
    'name' : 'Double Validation on Purchases',
    'version' : '1.1',
    'category': 'Purchase Management',
    'images' : ['images/purchase_validation.jpeg'],
    'depends' : ['base','purchase'],
    'author' : 'OpenERP SA',
    'description': """
Double-validation for purchases exceeding minimum amount.
=========================================================

This module modifies the purchase workflow in order to validate purchases that
exceeds minimum amount set by configuration wizard.
    """,
    'website': 'http://www.openerp.com',
    'data': [],
    'data': [
        'purchase_double_validation_workflow.xml',
        'purchase_double_validation_installer.xml',
        'purchase_double_validation_view.xml',
        'board_purchase_view.xml'
    ],
    'test': [
        'test/purchase_double_validation_demo.yml',
        'test/purchase_double_validation_test.yml'
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '00436592682510544157',

}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

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
    'name': 'Base module quality - To check the quality of other modules' ,
    'version': '1.0',
    'category': 'OpenERP SA Specific Modules/Base module quality',
    'description': """
The aim of this module is to check the quality of other modules.
================================================================

It defines a wizard on the list of modules in OpenERP, which allows you to
evaluate them on different criteria such as: the respect of OpenERP coding
standards, the speed efficiency...

This module also provides generic framework to define your own quality test.
For further info, coders may take a look into base_module_quality\README.txt

WARNING: This module cannot work as a ZIP file, you must unzip it before
using it, otherwise it may crash.
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': [],
    'update_xml': ['base_module_quality_wizard.xml', 'base_module_quality_view.xml', 'security/ir.model.access.csv'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0175119475677',
    'images': ['images/base_module_quality1.jpeg','images/base_module_quality2.jpeg','images/base_module_quality3.jpeg']
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

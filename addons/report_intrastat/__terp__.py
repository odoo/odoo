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
    'name': 'Intrastat Reporting - Reporting',
    'version': '1.0',
    'category': 'Generic Modules/Inventory Control',
    'description': """A module that adds intrastat reports.""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'product', 'stock', 'sale', 'purchase'],
    'init_xml': ['report_intrastat_data.xml'],
    'update_xml': [
        'security/ir.model.access.csv',
        'report_intrastat_view.xml',
        'intrastat_report.xml'
    ],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0056982189085',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

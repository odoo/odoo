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
    'name': 'Intrastat Reporting',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
A module that adds intrastat reports.
=====================================

This module gives the details of the goods traded between the countries of
European Union.""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base', 'product', 'stock', 'sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'report_intrastat_view.xml',
        'intrastat_report.xml',
        'report_intrastat_data.xml',
        'views/report_intrastatinvoice.xml'
    ],
    'demo': [],
    'test': ['test/report_intrastat_report.yml'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

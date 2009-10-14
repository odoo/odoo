# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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
    'name': 'Timesheet - Reporting',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """Module to add timesheet views like
    All Month, Timesheet By User, Timesheet Of Month, Timesheet By Account""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['hr_timesheet', 'hr_timesheet_invoice'],
    'init_xml': [],
    'update_xml': ['security/ir.model.access.csv', 'report_timesheet_view.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0078701510301',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

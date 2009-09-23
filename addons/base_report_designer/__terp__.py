# -*- encoding: utf-8 -*-
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
    'name': 'Report designer interface module',
    'version': '0.1',
    'category': 'Generic Modules/Base',
    'description': """
This module adds wizards to import/export documents to be edited in
OpenOffice.
""",
    'author': 'Tiny',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': ['base_report_data.xml'],
    'update_xml': ['base_report_designer_wizard.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0056379010493',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

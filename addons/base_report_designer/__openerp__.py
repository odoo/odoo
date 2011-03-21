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
    'name': 'Report designer interface module',
    'version': '0.1',
    'category': 'Tools',
    'description': """
This module is used along with OpenERP OpenOffice plugin.
You have to first install the plugin which is available at
http://www.openerp.com

This module adds wizards to Import/Export .sxw report that
you can modify in OpenOffice.Once you have modified it you can
upload the report using the same wizard.
""",
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'init_xml': ['wizard/base_report_design_view.xml'],
    'update_xml': ['base_report_designer_installer.xml'],
    'demo_xml': [],
    'installable': True,
    'active': False,
    'certificate': '0056379010493',
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

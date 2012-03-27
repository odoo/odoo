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
    "name" : "Report Designer",
    "version" : "1.0",
    "depends" : ["base", "base_setup"],
    "author" : "OpenERP SA",
    "complexity" : "expert",
    "category": "Tools",
    "description": """
Installer for reporting Hidden.
===============================

Makes the Reporting Hidden Configuration available from where you can install
modules like base_report_designer and base_report_creator.
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'res_config_view.xml',
    ],
    'demo_xml': [],
    'installable': True,
    'auto_install': False,
    'certificate' : '00764037194670093149',
    'images': ['images/config_reporting_Hidden.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

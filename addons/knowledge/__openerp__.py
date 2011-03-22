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
    "name" : "Knowledge Management System",
    "version" : "1.0",
    "depends" : ["base"],
    "author" : "OpenERP SA",
    "description": """
Installer for knowledge-based tools.
====================================

Makes the Knowledge Application Configuration available from where you can install
document and Wiki based tools.
    """,
    'website': 'http://www.openerp.com',
    'init_xml': [],
    'update_xml': [
        'security/knowledge_security.xml',
        'security/ir.model.access.csv',
        'knowledge_installer.xml',
        'knowledge_view.xml',
    ],
    'demo_xml': ['knowledge_demo.xml'],
    'installable': True,
    'active': False,
    'certificate' : '001278773815843749581',
    'images': ['images/1_config_knowledge.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

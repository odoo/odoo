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
    "name" : "Olap Schemes Management",
    "version" : "0.1",
    "author" : "Tiny",
    "website" : "http://www.openerp.com",
    "depends" : ["base"],
    "category" : "Generic Modules/Olap",
    "description": """
    Base module to manage Olap schemas. Cube designer.
    """,
    "init_xml" :  ["data/olap_data.xml"],
    "update_xml" : [
        "wizard/olap_query_logs_clear_view.xml",
        "wizard/olap_load_column_view.xml",
        "data/olap_wizard.xml",
        "data/olap_view.xml",
        "data/olap_cube_view.xml",
        "data/olap_fact_view.xml",
        "data/olap_cube_workflow.xml",
        "data/olap_security.xml",
        'security/ir.model.access.csv'
    ],
    "demo_xml" : ["data/olap_demo.xml"],
    "active": False,
    "installable": True
}

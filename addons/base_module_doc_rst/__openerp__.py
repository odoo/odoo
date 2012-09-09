# -*- encoding: utf-8 -*-
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
    'name': 'Generate Docs of Modules',
    'version': '1.0',
    'category': 'Tools',
    'description': """
This module generates the Technical Guides of selected modules in Restructured Text format (RST).
=================================================================================================

    * It uses the Sphinx (http://sphinx.pocoo.org) implementation of RST
    * It creates a tarball (.tgz file suffix) containing an index file and one file per module
    * Generates Relationship Graph
    """,
    'author': 'OpenERP SA',
    'website': 'http://www.openerp.com',
    'depends': ['base'],
    'data': [
        'base_module_doc_rst_view.xml',
        'wizard/generate_relation_graph_view.xml',
        'wizard/tech_guide_rst_view.xml',
        'module_report.xml',
    ],
    'demo': [],
    'installable': True,
    'certificate': '001288481437217734509',
    'images': ['images/base_module_doc_rst1.jpeg'],
}


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

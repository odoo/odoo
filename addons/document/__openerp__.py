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
    'name': 'Document Management System',
    'version': '2.1',
    'category': 'Knowledge Management',
    'description': """
This is a complete document management system.
==============================================
    * User Authentication
    * Document Indexation:- .pptx and .docx files are not supported in Windows platform.
    * Dashboard for Document that includes:
        * New Files (list)
        * Files by Resource Type (graph)
        * Files by Partner (graph)
        * Files Size by Month (graph)
""",
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com',
    'depends': ['knowledge', 'mail'],
    'data': [
        'security/document_security.xml',
        'document_view.xml',
        'document_data.xml',
        'wizard/document_configuration_view.xml',
        'security/ir.model.access.csv',
        'report/document_report_view.xml',
        'views/document.xml',
    ],
    'demo': [ 'document_demo.xml' ],
    'test': ['test/document_test2.yml'],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

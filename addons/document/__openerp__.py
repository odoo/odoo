# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


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

# -*- encoding: utf-8 -*-
{
    "name" : "Document Management - Reporting",
    "version" : "1.0",
    "author" : "Tiny",
    "depends" : ["document"],
    "category" : "Generic Modules/Document Management",
    "description": """
    Reporting for the Document Management module:
    * Files by my
    * Files by all users
    """,
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "report_document_view.xml",
        "security/ir.model.access.csv",
    ],
    "active": False,
    "installable": True
 }
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


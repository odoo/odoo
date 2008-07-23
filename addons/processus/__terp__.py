# -*- encoding: utf-8 -*-
{
    "name" : "Enterprise Processus",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com",
    "category" : "Generic Modules/Base",
    "description": """
This module allows you to manage your processus for the end-users.
    """,
    "depends" : ["base"],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        'processus_view.xml',
        'ir.model.access.csv',
        "processus_report.xml"],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


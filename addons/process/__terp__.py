# -*- encoding: utf-8 -*-
{
    "name" : "Enterprise Process",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com",
    "category" : "Generic Modules/Base",
    "description": """
This module allows you to manage your process for the end-users.
    """,
    "depends" : ["base"],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        'process_view.xml',
      ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


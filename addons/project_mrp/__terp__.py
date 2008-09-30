# -*- encoding: utf-8 -*-
{
    "name" : "Project Management - MRP Link",
    "version": "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com/module_project.html",
    "category" : "Generic Modules/Projects & Services",
    "depends" : ["project", 'mrp', "sale"],
    "description": """
This module is used to automatically create tasks base on different
procurements: sales order, manufacturing order, ...

It is mainly used to invoices services based on tasks by doing sales
order on services products.
""",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml": ["project_workflow.xml",
                   "process/project_mrp_process.xml"
                   ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


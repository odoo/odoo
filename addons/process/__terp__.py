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
    "depends" : ["base", "sale"],
    "init_xml" : [],
#    "demo_xml" : ['process_demo.xml'],
    "demo_xml" : [
        '../sale/process/sale_process.xml',
        '../hr_timesheet_sheet/process/hr_timesheet_sheet_process.xml',
        '../account/process/invoice_process.xml',
        '../account/process/statement_process.xml',
        '../project/process/task_process.xml',
        '../hr_timesheet/process/hr_timesheet_process.xml',
        '../purchase/process/purchase_process.xml',
        '../product/process/product_process.xml', 
    ]

    "update_xml" : [
        "security/ir.model.access.csv",
        'process_view.xml',
        '../sale/process/sale_process.xml'
    ],
    "active": False,
    "installable": True
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


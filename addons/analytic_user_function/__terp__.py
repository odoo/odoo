# -*- encoding: utf-8 -*-
{
    "name" : "Analytic User Function",
    "version" : "1.0",
    "depends" : ["hr_timesheet_sheet"],
    "author" : "Tiny",
    "description": """

    This module allows you to define what is the defaut function of a specific user on a given account. This is mostly used when a user encode his timesheet: the values are retrieved and the fields are auto-filled... but the possibility to change these values is still available.

    Obviously if no data has been recorded for the current account, the default value is given as usual by the employee data so that this module is perfectly compatible with older configurations.

    """,
    "website" : "http://tinyerp.com/",
    "category" : "Generic Modules/Others",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
            "analytic_user_function_view.xml",
            "security/ir.model.access.csv",
            ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


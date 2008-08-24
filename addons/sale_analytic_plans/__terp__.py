# -*- encoding: utf-8 -*-
{
    "name" : "Sales Analytic Distribution Management",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com/module_sale.html",
    "depends" : ["sale","account_analytic_plans"],
    "category" : "Generic Modules/Sales & Purchases",
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    The base module to manage analytic distribution and sales orders.
    """,
    "update_xml" : [
        "sale_analytic_plans_view.xml",
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


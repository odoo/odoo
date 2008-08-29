# -*- encoding: utf-8 -*-
{
    "name" : "Purchase Analytic Distribution Management",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com/module_sale.html",
    "depends" : ["purchase","account_analytic_plans"],
    "category" : "Generic Modules/Sales & Purchases",
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    The base module to manage analytic distribution and purchase orders.
    """,
    "update_xml" : [
        "purchase_analytic_plans_view.xml",
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


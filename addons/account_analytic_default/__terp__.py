# -*- encoding: utf-8 -*-
{
    "name" : "Account Analytic Default",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com",
    "category" : "Generic Modules/product_analytic_default",
    "description": """
Allows to automatically select analytic accounts based on criterions:
* Product
* Partner
* User
* Company
* Date
    """,
    "depends" : ['account'],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        "account_analytic_default_view.xml"],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


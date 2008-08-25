# -*- encoding: utf-8 -*-
{
    "name" : "Account Date check",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com/module_sale.html",
    "depends" : ["account"],
    "category" : "Generic Modules/Accounting",
    "init_xml" : [],
    "demo_xml" : [],
    "description": """
    * Adds a field on journals: "Allows date not in the period"
    * By default, this field is checked.

If this field is not checked, the system control that the date is in the
period when you create an account entry. Otherwise, it generates an
error message: "The date of your account move is not in the defined
period !"
    """,
    "update_xml" : [
        "account_date_check_view.xml",
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


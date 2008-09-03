# -*- encoding: utf-8 -*-
{
    "name" : "account_invoice_layout",
    "version" : "1.0",
    "depends" : ["base", "account"],
    "author" : "Tiny",
    "description": """
    This module provides some features to improve the layout of the invoices.

    It gives you the possibility to
        * order all the lines of an invoice
        * add titles, comment lines, sub total lines
        * draw horizontal lines and put page breaks
    
    Moreover, there is one option which allow you to print all the selected invoices with a given special message at the bottom of it. This feature can be very useful for printing your invoices with end-of-year wishes, special punctual conditions...

    """,
    "website" : "http://tinyerp.com/",
    "category" : "Generic Modules/Project & Services",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv",
        "account_invoice_layout_view.xml",
        "account_invoice_layout_report.xml",
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


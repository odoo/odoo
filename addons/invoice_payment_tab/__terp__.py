# -*- encoding: utf-8 -*-
{
    "name" : "Invoice payment tab",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://openerp.com",
    "category" : "Generic Modules/Accounting",
    "description": """
        This module defines a new tab on invoices, which contains all the payments made for this invoice. This improvement will allow accountants to easily manage due amounts and prepayments.
    """,
    "depends" : ["base","account"],
    "init_xml" : [],
    "demo_xml" : [],

    "update_xml" : ["invoice_payment_tab_view.xml"],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


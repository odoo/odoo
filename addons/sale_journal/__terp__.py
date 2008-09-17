# -*- encoding: utf-8 -*-
#
# Use the custom module to put your specific code in a separate module.
#
{
    "name" : "Managing sales and deliveries by journal",
    "version" : "1.0",
    "author" : "Tiny",
    "category" : "Generic Modules/Sales & Purchases",
    "website": "http://www.tinyerp.com",
    "depends" : ["stock","sale"],
    "demo_xml" : ['sale_journal_demo.xml'],
    "init_xml" : ['sale_journal_data.xml'],
    "update_xml" : [
        "security/ir.model.access.csv",
        "sale_journal_view.xml",
        "picking_journal_view.xml",
        "picking_journal_view_report.xml"
    ],
    "description" : """
    The sale journal modules allows you to categorize your
    sales and deliveries (packing lists) between different journals.
    This module is very helpfull for bigger companies that
    works by departments.

    You can use journal for different purposes, some examples:
    * isolate sales of different departments
    * journals for deliveries by truck or by UPS

    Journals have a responsible and evolves between different status:
    * draft, open, cancel, done.

    Batch operations can be processed on the different journals to
    confirm all sales at once, to validate or invoice packings, ...

    It also supports batch invoicing methods that can be configured by
    partners and sales orders, examples:
    * daily invoicing,
    * monthly invoicing, ...

    Some statistics by journals are provided.
    """,
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


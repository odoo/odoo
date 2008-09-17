# -*- encoding: utf-8 -*-
{
    "name" : "Reporting of Balancesheet for accounting",
    "version" : "1.0",
    "depends" : ["account"],
    "author" : "Tiny",
    "description": """Financial and accounting reporting""",
    "category" : "Generic Modules/Accounting",
    "init_xml" : [ ],
    "demo_xml" : [ ],
    "update_xml" : [
        "security/ir.model.access.csv",
        "account_view.xml",
        "account_report.xml",
        "account_data.xml",
    ],
#   "translations" : {
#       "fr": "i18n/french_fr.csv"
#   },
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


# -*- encoding: utf-8 -*-
{
    "name" : "Accounting and financial management-Compare Accounts",
    "version" : "1.1",
    "depends" : ["account"],
    "author" : "Tiny",
    "description": """Account Balance Module is an added functionality to the Financial Management module.

    This module gives you the various options for printing balance sheet.

    1. You can compare the balance sheet for different years.

    2. You can set the cash or percentage comparision between two years.

    3. You can set the referencial account for the percentage comparision for particular years.

    4. You can select periods as an actual date or periods as creation date.

    5. You have an option to print the desired report in Landscape format.
    """,
    "website" : "http://tinyerp.com/account_balance.html",
    "category" : "Generic Modules/Accounting",
    "init_xml" : [
    ],
    "demo_xml" : [],
    "update_xml" : ["account_report.xml","account_wizard.xml",],
#    "translations" : {
#        "fr": "i18n/french_fr.csv"
#    },
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


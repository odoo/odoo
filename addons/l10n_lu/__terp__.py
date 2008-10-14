{
        "name" : "l10n_lu",
        "version" : "1.0",
        "author" : "Tiny",
        "website" : "http://openerp.com",
        "category" : "Vertical Modules/Parametrization",
        "description": """ 
This module install:

    *the KLUWER Chart of Accounts,
    *the Tax Code Chart for Luxembourg
    *the main taxes used in Luxembourg""",
        "depends" : ["account","account_report"],
        "init_xml" : [ ],
        "demo_xml" : [ "account.report.report.csv" ],
        "update_xml" : [
            "l10n_lu_data.xml",
            "l10n_lu_wizard.xml",
            "l10n_lu_report.xml",
        ],
        "installable": True
} 

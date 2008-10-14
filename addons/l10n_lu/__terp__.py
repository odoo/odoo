{
        "name" : "l10n_lu",
        "version" : "1.0",
        "author" : "Tiny",
        "website" : "http://tinyerp.com",
        "category" : "Vertical Modules/Parametrization",
        "description": """ 
This module install 
* the KLUWER Chart of Accounts,
* the Tax Code Chart for Luxembourg
* the main taxes used in Luxembourg
""",
        "depends" : ["account"],
        "init_xml" : [ ],
        "demo_xml" : [ ],
        "update_xml" : [
            "l10n_lu_data.xml",
            "l10n_lu_report.xml",
            "l10n_lu_wizard.xml"
        ],
        "installable": True
} 

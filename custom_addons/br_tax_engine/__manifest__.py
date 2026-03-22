{
    "name": "BR Tax Engine",
    "version": "19.0.1.0.0",
    "summary": "Motor tributario temporal brasileiro",
    "category": "Localization/Brazil",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["br_account", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/br_tax_rules_legacy_2025.xml",
        "data/br_tax_rules_cbs_ibs_2026.xml",
        "data/br_cfop_table.xml",
        "data/br_cst_icms.xml",
        "data/br_cst_pis_cofins.xml",
    ],
    "installable": True,
    "application": False,
}


{
    "name": "BR Simples",
    "version": "19.0.1.0.0",
    "summary": "Regime do Simples Nacional",
    "category": "Localization/Brazil",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["br_tax_engine", "br_account", "account"],
    "data": [
        "security/ir.model.access.csv",
        "data/br_simples_anexos_2024.xml",
        "data/br_simples_anexos_2025.xml",
    ],
    "installable": True,
    "application": False,
}


{
    "name": "BR HR Payroll",
    "version": "19.0.1.0.0",
    "summary": "Tabelas brasileiras de folha",
    "category": "Localization/Brazil",
    "author": "Kodoo",
    "license": "LGPL-3",
    "depends": ["br_esocial", "hr_payroll_community", "hr_payroll_account_community"],
    "data": [
        "security/ir.model.access.csv",
        "data/br_inss_tabela_2025.xml",
        "data/br_irrf_tabela_2025.xml",
        "data/br_salary_rules.xml",
    ],
    "installable": True,
    "application": False,
}


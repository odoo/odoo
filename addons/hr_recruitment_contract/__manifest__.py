# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Recruitment - Contract",
    "version": "1.0",
    "category": "Human Resources/Recruitment",
    "sequence": 90,
    "summary": "Get wage statistics from current contracts",
    "description": "",
    "website": "https://www.odoo.com/page/recruitment",
    "depends": ["hr_recruitment", "hr_contract",],
    "data": [
        "security/ir.model.access.csv",
        "report/hr_contract_wage_views.xml",
        "views/hr_recruitment_views.xml",
    ],
    "installable": True,
    "auto_install": True,
    "application": False,
}

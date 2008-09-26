# -*- encoding: utf-8 -*-
{
    "name" : "Budget Management",
    "version" : "1.0",
    "author" : "Tiny",
    "website" : "http://tinyerp.com/module_crossovered_budget.html",
    "category" : "Generic Modules/Accounting",
    "description": """This module allow accountants to manage analytic and crossovered budgets.

    Once the Master Budgets and the Budgets defined (in Financial Management/Budgets/), the Project Managers can set the planned amount on each Analytic Account.

    The accountant has the possibility to see the total of amount planned for each Budget and Master Budget in order to ensure the total planned is not greater/lower than what he planned for this Budget/Master Budget. Each list of record can also be switched to a graphical view of it.

    Three reports are available:
        1. The first is available from a list of Budgets. It gives the spreading, for these Budgets, of the Analytic Accounts per Master Budgets.

        2. The second is a summary of the previous one, it only gives the spreading, for the selected Budgets, of the Analytic Accounts.

        3. The last one is available from the Analytic Chart of Accounts. It gives the spreading, for the selected Analytic Accounts, of the Master Budgets per Budgets.

""",
    "depends" : ["account"],
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
        "security/ir.model.access.csv","account_budget_wizard.xml",
        "crossovered_budget_view.xml","crossovered_budget_report.xml","crossovered_budget_workflow.xml"
    ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


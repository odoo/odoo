# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Multiple Analytic Plans',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
This module allows to use several analytic plans according to the general journal.
==================================================================================

Here multiple analytic lines are created when the invoice or the entries
are confirmed.

For example, you can define the following analytic structure:
-------------------------------------------------------------
  * **Projects**
      * Project 1
          + SubProj 1.1
          
          + SubProj 1.2

      * Project 2
      
  * **Salesman**
      * Eric
      
      * Fabien

Here, we have two plans: Projects and Salesman. An invoice line must be able to write analytic entries in the 2 plans: SubProj 1.1 and Fabien. The amount can also be split.
 
The following example is for an invoice that touches the two subprojects and assigned to one salesman:
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
**Plan1:**

    * SubProject 1.1 : 50%
    
    * SubProject 1.2 : 50%
    
**Plan2:**
    Eric: 100%

So when this line of invoice will be confirmed, it will generate 3 analytic lines,for one account entry.

The analytic plan validates the minimum and maximum percentage at the time of creation of distribution models.
        """,
    'website': 'https://www.odoo.com/page/accounting',
    'depends': ['account', 'account_analytic_default'],
    'data': [
        'security/account_analytic_plan_security.xml',
        'security/ir.model.access.csv',
        'account_analytic_plans_view.xml',
        'account_analytic_plans_report.xml',
        'wizard/analytic_plan_create_model_view.xml',
        'wizard/account_crossovered_analytic_view.xml',
        'views/report_crossoveredanalyticplans.xml',
        'views/account_analytic_plans.xml',
    ],
    'demo': [],
    'test': ['test/acount_analytic_plans_report.yml'],
    'installable': True,
    'auto_install': False,
}

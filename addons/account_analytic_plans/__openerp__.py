# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

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
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/accounting',
    'images': ['images/analytic_plan.jpeg'],
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

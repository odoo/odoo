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
    'name': 'Payment Follow-up Management',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
Module to automate letters for unpaid invoices, with multi-level recalls.
=========================================================================

You can define your multiple levels of recall through the menu:
---------------------------------------------------------------
    Configuration / Follow-up / Follow-up Levels
    
Once it is defined, you can automatically print recalls every day through simply clicking on the menu:
------------------------------------------------------------------------------------------------------
    Payment Follow-Up / Send Email and letters

It will generate a PDF / send emails / set manual actions according to the the different levels 
of recall defined. You can define different policies for different companies. 

Note that if you want to check the follow-up level for a given partner/account entry, you can do from in the menu:
------------------------------------------------------------------------------------------------------------------
    Reporting / Accounting / **Follow-ups Analysis

""",
    'author': 'OpenERP SA',
    'website': 'https://www.odoo.com/page/billing',
    'depends': ['account_accountant', 'mail'],
    'data': [
        'security/account_followup_security.xml',
        'security/ir.model.access.csv',
        'report/account_followup_report.xml',
        'account_followup_data.xml',
        'account_followup_view.xml',
        'account_followup_customers.xml',
        'wizard/account_followup_print_view.xml',
        'res_config_view.xml',
        'views/report_followup.xml',
        'account_followup_reports.xml'
    ],
    'demo': ['account_followup_demo.xml'],
    'test': [
        'test/account_followup.yml',
    ],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

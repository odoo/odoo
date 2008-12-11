# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2008 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    "name" : "Analytic Journal Billing Rate",
    "version" : "1.0",
    "depends" : ["analytic_user_function", "account", "hr_timesheet_invoice"],
    "author" : "Tiny",
    "description": """

    This module allows you to define what is the defaut invoicing rate for a specific journal on a given account. This is mostly used when a user encode his timesheet: the values are retrieved and the fields are auto-filled... but the possibility to change these values is still available.

    Obviously if no data has been recorded for the current account, the default value is given as usual by the account data so that this module is perfectly compatible with older configurations.

    """,
    "website" : "http://www.openerp.com",
    "category" : "Generic Modules/Others",
    "init_xml" : [],
    "demo_xml" : [],
    "update_xml" : [
            "analytic_journal_billing_rate_view.xml",
            "security/ir.model.access.csv",
            ],
    "active": False,
    "installable": True
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


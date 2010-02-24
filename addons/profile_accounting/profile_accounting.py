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

from osv import fields, osv
import pooler

class profile_accounting_config_install_modules_wizard(osv.osv_memory):
    _name = 'profile.accounting.config.install_modules_wizard'
    _inherit = 'res.config.installer'

    _columns = {
        'account_analytic_analysis':fields.boolean('Analytic Accounting'),
        'account_analytic_plans':fields.boolean('Multiple Analytic Plans'),
        'account_payment':fields.boolean('Suppliers Payment Management'),
        'account_asset':fields.boolean('Asset Management'),
        'hr_timesheet_invoice':fields.boolean('Invoice on Analytic Entries'),
        'account_budget':fields.boolean('Budgets', help="Helps you to manage financial and analytic budgets."),
        'board_document':fields.boolean('Document Management', help="The Document Management System of Open ERP allows you to store, browse, automatically index, search and preview all kind of documents (internal documents, printed reports, calendar system). It opens an FTP access for the users to easily browse association's document."),
    }
profile_accounting_config_install_modules_wizard()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

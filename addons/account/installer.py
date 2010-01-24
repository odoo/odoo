# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

class account_installer(osv.osv_memory):
    _name = 'account.installer'
    _inherit = 'res.config.installer'

    _columns = {
        # Accounting
        'account_analytic_default':fields.boolean('Analytic Accounting',
            help="Automatically selects analytic accounts based on various "
                 "criteria."),
        'account_analytic_plans':fields.boolean('Multiple Analytic Plans',
            help="Allows invoice lines to impact multiple analytic accounts "
                 "simultaneously."),
        'account_payment':fields.boolean('Suppliers Payment Management',
            help="Streamlines invoice payment and creates hooks to plug "
                 "automated payment systems in."),
        'account_followup':fields.boolean('Followups Management',
            help="Helps you generate reminder letters for unpaid invoices, "
                 "including multiple levels of reminding and customized "
                 "per-partner policies."),
        'account_asset':fields.boolean('Assets Management',
            help="Enables asset management in the accounting application, "
                 "including asset categories and usage periods.")
        }
    _defaults = {
        'account_analytic_default':True,
        }
account_installer()

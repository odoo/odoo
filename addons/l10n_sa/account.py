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

import logging
from datetime import datetime
from dateutil.relativedelta import relativedelta
from operator import itemgetter
import time

import openerp
from openerp import SUPERUSER_ID, api
from openerp import tools
from openerp.osv import fields, osv, expression
from openerp.tools.translate import _
from openerp.tools.float_utils import float_round as round
from openerp.tools.safe_eval import safe_eval as eval

import openerp.addons.decimal_precision as dp

class account_journal(osv.osv):
    _inherit = "account.journal"

    _defaults = {
        'entry_posted' : True,
        'allow_date' : True,
        }

    def create_sequence(self, cr, uid, vals, context=None):
        """ Create new no_gap entry sequence for every new Joural
        """
        # in account.journal code is actually the prefix of the sequence
        # whereas ir.sequence code is a key to lookup global sequences.            
        prefix = vals['code'].upper()

        seq = {
            'name': vals['name'],
            'implementation':'no_gap',
            'prefix': prefix + "/%(y)s%(month)s%(day)s%(h24)s/",
            'padding': 4,
            'number_increment': 1
        }
        if 'company_id' in vals:
            seq['company_id'] = vals['company_id']
        return self.pool.get('ir.sequence').create(cr, uid, seq)
    

class wizard_multi_charts_accounts(osv.osv_memory):
    _inherit='wizard.multi.charts.accounts'
    
    def _prepare_bank_journal(self, cr, uid, line, current_num, default_account_id, company_id, context=None):
        obj_data = self.pool.get('ir.model.data')
        obj_journal = self.pool.get('account.journal')
        
        for num in xrange(current_num, 100):
            # journal_code has a maximal size of 5, hence we can enforce the boundary num < 100
            journal_code = line['account_type'] == 'cash' and _('CSH')[:3] + str(num) or _('BNK')[:3] + str(num)
            ids = obj_journal.search(cr, uid, [('code', '=', journal_code), ('company_id', '=', company_id)], context=context)
            if not ids:
                break
        else:
            raise osv.except_osv(_('Error!'), _('Cannot generate an unused journal code.'))

        vals = {
                'name': line['acc_name'],
                'code': journal_code,
                'type': line['account_type'] == 'cash' and 'cash' or 'bank',
                'company_id': company_id,
                'analytic_journal_id': False,
                'currency': False,
                'default_credit_account_id': default_account_id,
                'default_debit_account_id': default_account_id,
        }
        if line['currency_id']:
            vals['currency'] = line['currency_id']
        
        return vals
    
    def _prepare_all_journals(self, cr, uid, chart_template_id, acc_template_ref, company_id, context=None):
        def _get_analytic_journal(journal_type):
            # Get the analytic journal
            data = False
            try:
                if journal_type in ('sale', 'sale_refund'):
                    data = obj_data.get_object_reference(cr, uid, 'account', 'analytic_journal_sale')
                elif journal_type in ('purchase', 'purchase_refund'):
                    data = obj_data.get_object_reference(cr, uid, 'account', 'exp')
                elif journal_type == 'general':
                    pass
            except ValueError:
                pass
            return data and data[1] or False

        def _get_default_account(journal_type, type='debit'):
            # Get the default accounts
            default_account = False
            if journal_type in ('sale', 'sale_refund'):
                default_account = acc_template_ref.get(template.property_account_income.id)
            elif journal_type in ('purchase', 'purchase_refund'):
                default_account = acc_template_ref.get(template.property_account_expense.id)
            elif journal_type == 'situation':
                if type == 'debit':
                    default_account = acc_template_ref.get(template.property_account_expense_opening.id)
                else:
                    default_account = acc_template_ref.get(template.property_account_income_opening.id)
            return default_account

        journal_names = {
            'sale': _('Sales/Income Journal'),
            'purchase': _('Purchase/Expenses Journal'),
            'sale_refund': _('Sales Refund Journal'),
            'purchase_refund': _('Purchase Refund Journal'),
            'general': _('Miscellaneous Journal'),
            'situation': _('Opening Entries Journal'),
        }
        journal_codes = {
            'sale': _('SALE'),
            'purchase': _('PURC'),
            'sale_refund': _('SRFD'),
            'purchase_refund': _('PRFD'),
            'general': _('MISC'),
            'situation': _('OPEJ'),
        }

        obj_data = self.pool.get('ir.model.data')
        analytic_journal_obj = self.pool.get('account.analytic.journal')
        template = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)

        journal_data = []
        for journal_type in ['sale', 'purchase', 'sale_refund', 
                             'purchase_refund', 'general', 'situation']:
            vals = {
                'type': journal_type,
                'name': journal_names[journal_type],
                'code': journal_codes[journal_type],
                'company_id': company_id,
                'centralisation': journal_type == 'situation',
                'analytic_journal_id': _get_analytic_journal(journal_type),
                'default_credit_account_id': _get_default_account(journal_type, 'credit'),
                'default_debit_account_id': _get_default_account(journal_type, 'debit'),
            }
            journal_data.append(vals)
        return journal_data
    
# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 ITS-1 (<http://www.its1.lv/>)
#                       E-mail: <info@its1.lv>
#                       Address: <Vienibas gatve 109 LV-1058 Riga Latvia>
#                       Phone: +371 66116534
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

import openerp.tools
from openerp.osv import  osv, fields
import openerp.addons
import os
from openerp.tools.translate import _

class account_chart_template(osv.osv):
    _inherit = 'account.chart.template'

    _columns = {
        'cash_account_view_id': fields.many2one('account.account.template', 'Cash Account')
    }

    _defaults = {
        'code_digits': 4
    }

class wizard_multi_charts_accounts(osv.osv_memory):
    _inherit = 'wizard.multi.charts.accounts'

    def onchange_chart_template_id(self, cr, uid, ids, chart_template_id=False, context=None):
        res = {}
        tax_templ_obj = self.pool.get('account.tax.template')
        res['value'] = {'complete_tax_set': False, 'sale_tax': False, 'purchase_tax': False}
        if chart_template_id:
            data = self.pool.get('account.chart.template').browse(cr, uid, chart_template_id, context=context)
            res['value'].update({'complete_tax_set': data.complete_tax_set})
            if data.complete_tax_set:
            # default tax is given by the lowest sequence. For same sequence we will take the latest created as it will be the case for tax created while isntalling the generic chart of account
                sale_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                              , "=", chart_template_id), ('description', '=', 'PVN-SR')])
                purchase_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                              , "=", chart_template_id), ('description', '=', 'Pr-SR')], order="sequence, id desc")
                res['value'].update({'sale_tax': sale_tax_ids and sale_tax_ids[0] or False, 'purchase_tax': purchase_tax_ids and purchase_tax_ids[0] or False})

            if data.code_digits:
               res['value'].update({'code_digits': data.code_digits})
        return res

    def default_get(self, cr, uid, fields, context=None):
        res = super(wizard_multi_charts_accounts, self).default_get(cr, uid, fields, context=context) 
        tax_templ_obj = self.pool.get('account.tax.template')

        if 'bank_accounts_id' in fields:
            res.update({'bank_accounts_id': [{'acc_name': _('Kase'), 'account_type': 'cash'},{'acc_name': _('Banka'), 'account_type': 'bank'}]})
        if 'company_id' in fields:
            res.update({'company_id': self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0].company_id.id})
        if 'seq_journal' in fields:
            res.update({'seq_journal': True})

        ids = self.pool.get('account.chart.template').search(cr, uid, [('name', '=', 'Latvija – saimnieciskā aprēķina')], context=context)
        if ids:
            if 'chart_template_id' in fields:
                res.update({'only_one_chart_template': len(ids) == 1, 'chart_template_id': ids[0]})
            if 'sale_tax' in fields:
                sale_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                              , "=", ids[0]), ('description', '=', 'PVN-SR')])
                res.update({'sale_tax': sale_tax_ids and sale_tax_ids[0] or False})
            if 'purchase_tax' in fields:
                purchase_tax_ids = tax_templ_obj.search(cr, uid, [("chart_template_id"
                                          , "=", ids[0]), ('description', '=', 'Pr-SR')])
                res.update({'purchase_tax': purchase_tax_ids and purchase_tax_ids[0] or False})
        res.update({
            'purchase_tax_rate': 21.0,
            'sale_tax_rate': 21.0,
        })
        return res

    def _remove_unnecessary_account_fiscal_position_tax_templates(self, cr, uid, ids, context=None):
        acc_fpos_tax_tmp_obj = self.pool.get('account.fiscal.position.tax.template')
        data_obj = self.pool.get('ir.model.data')
        rem_ids = []
        rem_list = [
            'fiscal_position_normal_taxes',
            'fiscal_position_tax_exempt'
        ]
        for item in rem_list:
            rem_ids.append(data_obj.get_object(cr, uid, 'account', item).id)
        res = {}
        if rem_ids:
            res = acc_fpos_tax_tmp_obj.unlink(cr, uid, rem_ids)
        return res

    def _remove_unnecessary_account_fiscal_position_templates(self, cr, uid, ids, context=None):
        acc_fpos_tmp_obj = self.pool.get('account.fiscal.position.template')
        data_obj = self.pool.get('ir.model.data')
        rem_ids = []
        rem_list = [
            'fiscal_position_normal_taxes_template1',
            'fiscal_position_tax_exempt_template2'
        ]
        for item in rem_list:
            rem_ids.append(data_obj.get_object(cr, uid, 'account', item).id)
        res = {}
        if rem_ids:
            res = acc_fpos_tmp_obj.unlink(cr, uid, rem_ids)
        return res

    def _remove_unnecessary_account_tax_templates(self, cr, uid, ids, context=None):
        acc_tax_tmp_obj = self.pool.get('account.tax.template')
        data_obj = self.pool.get('ir.model.data')
        rem_ids = []
        rem_list = [
            'otaxs',
            'otaxr',
            'otaxx',
            'otaxo',
            'itaxs',
            'itaxr',
            'itaxx',
            'itaxo'
        ]
        for item in rem_list:
            rem_ids.append(data_obj.get_object(cr, uid, 'account', item).id)
        res = {}
        if rem_ids:
            res = acc_tax_tmp_obj.unlink(cr, uid, rem_ids)
        return res

    def _remove_unnecessary_account_tax_code_templates(self, cr, uid, ids, context=None):
        acc_tax_code_tmp_obj = self.pool.get('account.tax.code.template')
        data_obj = self.pool.get('ir.model.data')
        rem_ids = []
        rem_list = [
            'tax_code_chart_root',
            'tax_code_balance_net',
            'tax_code_input',
            'tax_code_input_S',
            'tax_code_input_R',
            'tax_code_input_X',
            'tax_code_input_O',
            'tax_code_output',
            'tax_code_output_S',
            'tax_code_output_R',
            'tax_code_output_X',
            'tax_code_output_O',
            'tax_code_base_net',
            'tax_code_base_purchases',
            'tax_code_purch_S',
            'tax_code_purch_R',
            'tax_code_purch_X',
            'tax_code_purch_O',
            'tax_code_base_sales',
            'tax_code_sales_S',
            'tax_code_sales_R',
            'tax_code_sales_X',
            'tax_code_sales_O'
        ]
        for item in rem_list:
            rem_ids.append(data_obj.get_object(cr, uid, 'account', item).id)
        res = {}
        if rem_ids:
            res = acc_tax_code_tmp_obj.unlink(cr, uid, rem_ids)
        return res

    def _remove_unnecessary_account_templates(self, cr, uid, ids, context=None):
        acc_template_obj = self.pool.get('account.account.template')
        data_obj = self.pool.get('ir.model.data')
        rem_ids = []
        rem_list = [
            'conf_chart0',
            'conf_bal',
            'conf_fas',
            'conf_xfa',
            'conf_nca',
            'conf_cas',
            'conf_stk',
            'conf_a_recv',
            'conf_ova',
            'conf_bnk',
            'conf_o_income',
            'conf_cli',
            'conf_a_pay',
            'conf_iva',
            'conf_a_reserve_and_surplus',
            'conf_o_expense',
            'conf_gpf',
            'conf_rev',
            'conf_a_sale',
            'conf_cos',
            'conf_cog',
            'conf_ovr',
            'conf_a_expense',
            'conf_a_salary_expense',
            'conf_a_sale',
            'conf_a_expense'
        ]
        for item in rem_list:
            rem_ids.append(data_obj.get_object(cr, uid, 'account', item).id)
        res = {}
        if rem_ids:
            res = acc_template_obj.unlink(cr, uid, rem_ids)
        return res

    def _remove_unnecessary_account_charts(self, cr, uid, ids, context=None):
        acc_chart_tmp_obj = self.pool.get('account.chart.template')
        data_obj = self.pool.get('ir.model.data')
        chart_tmp_id = data_obj.get_object(cr, uid, 'account', 'configurable_chart_template').id
        res = acc_chart_tmp_obj.unlink(cr, uid, chart_tmp_id)
        return res

    def _remove_unnecessary_account_types(self, cr, uid, ids, context=None):
        acc_type_obj = self.pool.get('account.account.type')
        data_obj = self.pool.get('ir.model.data')
        rem_ids = []
        rem_list = [
            'data_account_type_receivable',
            'data_account_type_payable',
            'data_account_type_bank',
            'data_account_type_cash',
            'data_account_type_asset',
            'account_type_asset_view1',
            'data_account_type_liability',
            'account_type_liability_view1',
            'data_account_type_income',
            'account_type_income_view1',
            'data_account_type_expense',
            'account_type_expense_view1',
#            'account_type_cash_equity',
            'conf_account_type_equity',
            'conf_account_type_tax',
            'conf_account_type_chk',
        ]
        for item in rem_list:
            rem_ids.append(data_obj.get_object(cr, uid, 'account', item).id)

        res = {}
        mod_obj = self.pool.get('ir.module.module')
        acc_mod_ids = mod_obj.search(cr, uid, [('name','=','account')])
        allow = True
        if acc_mod_ids:
            acc_mod = mod_obj.browse(cr, uid, acc_mod_ids[0])
            if acc_mod.demo == True:
                allow = False
        if rem_ids and allow == True:
            res = acc_type_obj.unlink(cr, uid, rem_ids)
        return res

    def execute(self, cr, uid, ids, context=None):
        self._remove_unnecessary_account_fiscal_position_tax_templates(cr, uid, ids, context=context)
        self._remove_unnecessary_account_fiscal_position_templates(cr, uid, ids, context=context)
        self._remove_unnecessary_account_tax_templates(cr, uid, ids, context=context)
        self._remove_unnecessary_account_tax_code_templates(cr, uid, ids, context=context)
        self._remove_unnecessary_account_templates(cr, uid, ids, context=context)
        self._remove_unnecessary_account_charts(cr, uid, ids, context=context)
        self._remove_unnecessary_account_types(cr, uid, ids, context=context)
        return super(wizard_multi_charts_accounts, self).execute(cr, uid, ids, context=context)

    def _prepare_bank_account(self, cr, uid, line, new_code, acc_template_ref, ref_acc, company_id, context=None):
        '''
        This function prepares the value to use for the creation of the default debit and credit accounts of a
        bank journal created through the wizard of generating COA from templates.

        :param line: dictionary containing the values encoded by the user related to his bank account
        :param new_code: integer corresponding to the next available number to use as account code
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :param ref_acc_bank: browse record of the account template set as root of all bank accounts for the chosen
            template
        :param ref_acc_cash: browse record of the account template set as root of all cash accounts for the chosen
            template
        :param company_id: id of the company for which the wizard is running
        :return: mapping of field names and values
        :rtype: dict
        '''
        obj_data = self.pool.get('ir.model.data')

        # Get the id of the user types fr-or cash and bank
        tmp = obj_data.get_object_reference(cr, uid, 'l10n_lv', 'account_type_2012_2_5')
        cash_type = tmp and tmp[1] or False
        tmp = obj_data.get_object_reference(cr, uid, 'l10n_lv', 'account_type_2012_2_5')
        bank_type = tmp and tmp[1] or False
        return {
            'name': line['acc_name'],
            'currency_id': line['currency_id'],
            'code': new_code,
            'type': 'other',
            'user_type': line['account_type'] == 'cash' and cash_type or bank_type,
            'parent_id': acc_template_ref[ref_acc.id] or False,
            'company_id': company_id,
        }

    def _create_bank_journals_from_o2m(self, cr, uid, obj_wizard, company_id, acc_template_ref, context=None):
        '''
        This function creates bank journals and its accounts for each line encoded in the field bank_accounts_id of the
        wizard.

        :param obj_wizard: the current wizard that generates the COA from the templates.
        :param company_id: the id of the company for which the wizard is running.
        :param acc_template_ref: the dictionary containing the mapping between the ids of account templates and the ids
            of the accounts that have been generated from them.
        :return: True
        '''
        obj_acc = self.pool.get('account.account')
        obj_journal = self.pool.get('account.journal')
        code_digits = obj_wizard.code_digits

        # Build a list with all the data to process
        journal_data = []
        if obj_wizard.bank_accounts_id:
            for acc in obj_wizard.bank_accounts_id:
                vals = {
                    'acc_name': acc.acc_name,
                    'account_type': acc.account_type,
                    'currency_id': acc.currency_id.id,
                }
                journal_data.append(vals)
        ref_acc_bank = obj_wizard.chart_template_id.bank_account_view_id
        ref_acc_cash = obj_wizard.chart_template_id.cash_account_view_id
        if journal_data and not ref_acc_bank.code:
            raise osv.except_osv(_('Configuration Error !'), _('The bank account defined on the selected chart of accounts hasn\'t a code.'))
        if journal_data and not ref_acc_cash.code:
            raise osv.except_osv(_('Configuration Error !'), _('The cash account defined on the selected chart of accounts hasn\'t a code.'))

        current_num_bank = 1
        current_num_cash = 1
        for line in journal_data:
            # Seek the next available number for the account code
            if line['account_type'] == 'bank':
                while True:
                    new_code_bank = str(ref_acc_bank.code.ljust(code_digits-len(str(current_num_bank)), '0')) + str(current_num_bank)
                    ids = obj_acc.search(cr, uid, [('code', '=', new_code_bank), ('company_id', '=', company_id)])
                    if not ids:
                        break
                    else:
                        current_num_bank += 1
            if line['account_type'] == 'cash':
                while True:
                    new_code_cash = str(ref_acc_cash.code.ljust(code_digits-len(str(current_num_cash)), '0')) + str(current_num_cash)
                    ids = obj_acc.search(cr, uid, [('code', '=', new_code_cash), ('company_id', '=', company_id)])
                    if not ids:
                        break
                    else:
                        current_num_cash += 1
            # Create the default debit/credit accounts for this bank journal
            if line['account_type'] == 'bank':
                vals_bank = self._prepare_bank_account(cr, uid, line, new_code_bank, acc_template_ref, ref_acc_bank, company_id, context=context)
                default_bank_account_id  = obj_acc.create(cr, uid, vals_bank, context=context)

            if line['account_type'] == 'cash':
                vals_cash = self._prepare_bank_account(cr, uid, line, new_code_cash, acc_template_ref, ref_acc_cash, company_id, context=context)
                default_cash_account_id  = obj_acc.create(cr, uid, vals_cash, context=context)

            #create the bank journal
            if line['account_type'] == 'bank':
                vals_journal_bank = self._prepare_bank_journal(cr, uid, line, current_num_bank, default_bank_account_id, company_id, context=context)
                obj_journal.create(cr, uid, vals_journal_bank)
                current_num_bank += 1

            if line['account_type'] == 'cash':
                vals_journal_cash = self._prepare_bank_journal(cr, uid, line, current_num_cash, default_cash_account_id, company_id, context=context)
                obj_journal.create(cr, uid, vals_journal_cash)
                current_num_cash += 1
        return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:


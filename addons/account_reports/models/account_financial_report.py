# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenErp S.A. (<http://odoo.com>).
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

from openerp import models, fields, api, _
from openerp.tools.safe_eval import safe_eval
from openerp.tools.misc import formatLang
from datetime import datetime
from dateutil.relativedelta import relativedelta


class FormulaLine(object):
    def __init__(self, obj, type='balance'):
        fields = dict((fn, 0.0) for fn in ['debit', 'credit', 'balance'])
        if type == 'balance':
            fields = obj.get_balance()[0]
        elif type == 'sum':
            if obj._name == 'account.financial.report.line':
                fields = obj.get_sum()
                self.amount_residual = fields['amount_residual']
            elif obj._name == 'account.move.line':
                self.amount_residual = 0.0
                field_names = ['debit', 'credit', 'balance', 'amount_residual']
                res = obj.compute_fields(field_names)
                if res.get(obj.id):
                    if obj.currency_id != obj.env.user.company_id.currency_id:
                        for n, v in fields.items():
                            fields[n] = obj.company_currency_id.compute(v, obj.env.user.company_id.currency_id)
                    for field in field_names:
                        fields[field] = res[obj.id][field]
                    self.amount_residual = fields['amount_residual']
        elif type == 'not_computed':
            for field in fields:
                fields[field] = obj.get(field, 0)
            self.amount_residual = obj.get('amount_residual', 0)
        self.balance = fields['balance']
        self.credit = fields['credit']
        self.debit = fields['debit']


class FormulaContext(dict):
    def __init__(self, reportLineObj, curObj=None, *data):
        self.reportLineObj = reportLineObj
        self.curObj = curObj
        return super(FormulaContext, self).__init__(data)

    def __getitem__(self, item):
        if self.get(item):
            return super(FormulaContext, self).__getitem__(item)
        if item == 'sum':
            res = FormulaLine(self.curObj, type='sum')
            self['sum'] = res
            return res
        if item == 'NDays':
            d1 = datetime.strptime(self.curObj.env.context['date_from'], "%Y-%m-%d")
            d2 = datetime.strptime(self.curObj.env.context['date_to'], "%Y-%m-%d")
            res = (d2 - d1).days
            self['NDays'] = res
            return res
        line_id = self.reportLineObj.search([('code', '=', item)], limit=1)
        if line_id:
            res = FormulaLine(line_id)
            self[item] = res
            return res
        return super(FormulaContext, self).__getitem__(item)


class ReportAccountFinancialReport(models.Model):
    _inherit = "account.financial.report"
    _description = "Account Report"

    def create_action_and_menu(self):
        client_action = self.env['ir.actions.client'].create({
            'name': self.get_title(),
            'tag': 'account_report_generic',
            'context': {
                'url': '/account/financial_report/' + str(self.id),
                'model': 'account.financial.report',
                'id': self.id,
            },
        })
        self.env['ir.ui.menu'].create({
            'name': self.get_title(),
            'parent_id': self.env['ir.model.data'].xmlid_to_res_id('account.menu_finance_reports'),
            'action': 'ir.actions.client,%s' % (client_action.id,),
        })
        self.write({'menuitem_created': True})

    @api.model
    def create(self, vals):
        res = super(ReportAccountFinancialReport, self).create(vals)
        res.create_action_and_menu()
        return res

    @api.multi
    def get_lines(self, context_id, line_id=None):
        if isinstance(context_id, int):
            context_id = self.env['account.financial.report.context'].browse(context_id)
        line_obj = self.line_ids
        if line_id:
            line_obj = self.env['account.financial.report.line'].search([('id', '=', line_id)])
        if context_id.comparison:
            line_obj = line_obj.with_context(periods=context_id.get_cmp_periods())
        res = line_obj.with_context(
            target_move=context_id.all_entries and 'all' or 'posted',
            cash_basis=self.report_type == 'date_range_cash' or context_id.cash_basis,
            strict_range=self.report_type == 'date_range_extended',
            aged_balance=self.report_type == 'date_range_extended',
        ).get_lines(self, context_id)
        return res

    def get_title(self):
        return self.name

    def get_name(self):
        return 'financial_report'

    @api.multi
    def get_report_type(self):
        return self.report_type

    def get_template(self):
        return 'account_reports.report_financial'


class AccountFinancialReportLine(models.Model):
    _inherit = "account.financial.report.line"
    _description = "Account Report Line"
    _order = "sequence"

    def get_sum(self, field_names=None):
        ''' Returns the sum of the amls in the domain '''
        if not field_names:
            field_names = ['debit', 'credit', 'balance', 'amount_residual']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            amls = self.env['account.move.line'].search(safe_eval(self.domain))
            compute = amls.compute_fields(field_names)
            for aml in amls:
                if compute.get(aml.id):
                    if aml.currency_id != self.env.user.company_id.currency_id:
                        for n, v in compute[aml.id].items():
                            compute[aml.id][n] = aml.company_currency_id.compute(v, self.env.user.company_id.currency_id)
                    for field in field_names:
                        res[field] += compute[aml.id][field]
        return res

    @api.one
    def get_balance(self, field_names=None):
        if not field_names:
            field_names = ['debit', 'credit', 'balance']
        res = dict((fn, 0.0) for fn in field_names)
        c = FormulaContext(self.env['account.financial.report.line'], self)
        if self.formulas:
            for f in self.formulas.split(';'):
                [field, formula] = f.split('=')
                field = field.strip()
                if field in field_names:
                    try:
                        res[field] = safe_eval(formula, c, nocopy=True)
                    except ValueError as err:
                        if 'division by zero' in err.args[0]:
                            res[field] = 0
                        else:
                            raise err
        return res

    def _format(self, value):
        if self.env.context.get('no_format'):
            return round(value, 1)
        if self.figure_type == 'float':
            currency_id = self.env.user.company_id.currency_id
            if currency_id.is_zero(value):
                #don't print -0.0 in reports
                value = abs(value)
            return formatLang(self.env, value, currency_obj=currency_id)
        if self.figure_type == 'percents':
            return str(round(value * 100, 1)) + '%'
        return round(value, 1)

    def _get_gb_name(self, gb_id):
        if self.groupby == 'account_id':
            return self.env['account.account'].browse(gb_id).name_get()[0][1]
        if self.groupby == 'user_type':
            return self.env['account.account.type'].browse(gb_id).name
        if self.groupby == 'partner_id':
            return self.env['res.partner'].browse(gb_id).name
        return gb_id

    def _build_cmp(self, balance, comp):
        if comp != 0:
            res = round((balance-comp)/comp * 100, 1)
            if (res > 0) != self.green_on_positive:
                return (str(res) + '%', 'color: red;')
            else:
                return (str(res) + '%', 'color: green;')
        else:
            return 'n/a'

    def _get_footnotes(self, type, target_id, context):
        footnotes = context.footnotes.filtered(lambda s: s.type == type and s.target_id == target_id)
        result = {}
        for footnote in footnotes:
            result.update({footnote.column: footnote.number})
        return result

    def _split_formulas(self):
        result = {}
        if self.formulas:
            for f in self.formulas.split(';'):
                [column, formula] = f.split('=')
                column = column.strip()
                result.update({column: formula})
        return result

    def eval_formula(self, financial_report, debit_credit, context):
        debit_credit = debit_credit and financial_report.debit_credit
        formulas = self._split_formulas()

        vals = self.get_balance(not debit_credit and ['balance'] or None)[0]

        results = {}
        if self.domain and self.groupby and self.show_domain != 'never':
            aml_obj = self.env['account.move.line']
            where_clause, where_params = aml_obj._query_get(domain=self.domain)

            groupby = self.groupby or 'id'
            select = ',COALESCE(SUM(\"account_move_line\".debit-\"account_move_line\".credit), 0),SUM(\"account_move_line\".amount_residual),\"account_move_line\".company_currency_id'
            if financial_report.debit_credit and debit_credit:
                select = ',SUM(\"account_move_line\".debit),SUM(\"account_move_line\".credit)' + select
            if self.env.context.get('cash_basis'):
                select = select.replace('debit', 'debit_cash_basis').replace('credit', 'credit_cash_basis')
            sql = "SELECT \"account_move_line\"." + groupby + "%s FROM \"account_move_line\" WHERE %s GROUP BY \"account_move_line\".company_currency_id,\"account_move_line\"." + groupby
            where_clause, where_params = aml_obj._query_get(domain=self.domain)
            query = sql % (select, where_clause)
            self.env.cr.execute(query, where_params)
            results = self.env.cr.fetchall()
            if financial_report.debit_credit and debit_credit:
                results = dict([(k[0], {'debit': k[1], 'credit': k[2], 'balance': k[3], 'amount_residual': k[4], 'currency_id': k[5]}) for k in results])
            else:
                results = dict([(k[0], {'balance': k[1], 'amount_residual': k[2], 'currency_id': k[3]}) for k in results])
            c = FormulaContext(self.env['account.financial.report.line'])
            if formulas:
                for key in results:
                    if results[key]['currency_id'] != self.env.user.company_id.currency_id.id:
                        currency_id = self.env['res.currency'].browse(results[key]['currency_id'])
                        del results[key]['currency_id']
                        for n, v in results[key].items():
                            results[key][n] = currency_id.compute(v, self.env.user.company_id.currency_id)
                    c['sum'] = FormulaLine(results[key], type='not_computed')
                    for col, formula in formulas.items():
                        if col in results[key]:
                            results[key][col] = safe_eval(formula, c, nocopy=True)
            to_del = []
            for key in results:
                if self.env.user.company_id.currency_id.is_zero(results[key]['balance']):
                    to_del.append(key)
            for key in to_del:
                del results[key]

        results.update({'line': vals})
        return results

    def _put_columns_together(self, data, domain_ids):
        res = dict((domain_id, []) for domain_id in domain_ids)
        for period in data:
            debit_credit = False
            if 'debit' in period['line']:
                debit_credit = True
            for domain_id in domain_ids:
                if debit_credit:
                    res[domain_id].append(period.get(domain_id, {'debit': 0})['debit'])
                    res[domain_id].append(period.get(domain_id, {'credit': 0})['credit'])
                res[domain_id].append(period.get(domain_id, {'balance': 0})['balance'])
        return res

    @api.multi
    def get_lines(self, financial_report, context):
        final_result_table = []
        comparison_table = context.get_periods()
        #build comparison table

        for line in self:
            res = []
            debit_credit = len(comparison_table) == 1
            domain_ids = {'line'}
            for period in comparison_table:
                period_from = period[0]
                period_to = period[1]
                if line.special_date_changer == 'from_beginning':
                    period_from = False
                if line.special_date_changer == 'to_beginning_of_period':
                    date_tmp = datetime.strptime(period[0], "%Y-%m-%d") - relativedelta(days=1)
                    period_to = date_tmp.strftime('%Y-%m-%d')
                r = line.with_context(date_from=period_from, date_to=period_to).eval_formula(financial_report, debit_credit, context)
                debit_credit = False
                res.append(r)
                domain_ids.update(set(r.keys()))

            res = self._put_columns_together(res, domain_ids)
            if line.hide_if_zero and sum([k == 0 and [True] or [] for k in res['line']], []):
                continue

            # Post-processing ; creating line dictionnary, building comparison, computing total for extended, formatting
            vals = {
                'id': line.id,
                'name': line.name,
                'type': 'line',
                'level': line.level,
                'footnotes': line._get_footnotes('line', line.id, context),
                'columns': res['line'],
                'unfoldable': len(domain_ids) > 1 and line.show_domain != 'always',
                'unfolded': line in context.unfolded_lines or line.show_domain == 'always',
            }
            if line.action_id:
                vals['action_id'] = line.action_id.id
            domain_ids.remove('line')
            lines = [vals]
            groupby = line.groupby or 'aml'
            if line in context.unfolded_lines or line.show_domain == 'always':
                for domain_id in domain_ids:
                    vals = {
                        'id': domain_id,
                        'name': line._get_gb_name(domain_id),
                        'level': line.level + 2,
                        'type': groupby,
                        'footnotes': line._get_footnotes(groupby, domain_id, context),
                        'columns': res[domain_id],
                    }
                    lines.append(vals)

            for vals in lines:
                if financial_report.report_type == 'date_range_extended':
                    vals['columns'].append(sum(vals['columns']))
                if len(comparison_table) == 2:
                    vals['columns'].append(line._build_cmp(vals['columns'][0], vals['columns'][1]))
                    for i in [0, 1]:
                        vals['columns'][i] = line._format(vals['columns'][i])
                else:
                    vals['columns'] = map(line._format, vals['columns'])
                if not line.formulas:
                    vals['columns'] = ['' for k in vals['columns']]

            new_lines = line.children_ids.get_lines(financial_report, context)

            result = []
            if line.level > 0:
                result += lines
            result += new_lines
            if line.level <= 0:
                result += lines
            final_result_table += result

        return final_result_table


class AccountFinancialReportContext(models.TransientModel):
    _name = "account.financial.report.context"
    _description = "A particular context for a financial report"
    _inherit = "account.report.context.common"

    def get_report_obj(self):
        return self.report_id

    report_id = fields.Many2one('account.financial.report', 'Linked financial report', help='Only if financial report')
    unfolded_lines = fields.Many2many('account.financial.report.line', 'context_to_line', string='Unfolded lines')

    @api.model
    def create(self, vals):
        force_fy = False
        if 'force_fy' in vals:
            del vals['force_fy']
            force_fy = True
        res = super(AccountFinancialReportContext, self).create(vals)
        if force_fy:
            dates = self.env.user.company_id.compute_fiscalyear_dates(datetime.today())
            res.write({
                'date_from': dates['date_from'],
                'date_to': dates['date_to'],
                'date_filter': 'this_year'
            })
        return res

    @api.multi
    def remove_line(self, line_id):
        self.write({'unfolded_lines': [(3, line_id)]})

    @api.multi
    def add_line(self, line_id):
        self.write({'unfolded_lines': [(4, line_id)]})

    def get_balance_date(self):
        if self.report_id.report_type == 'no_date_range':
            return self.get_full_date_names(self.date_to)
        return self.get_full_date_names(self.date_to, self.date_from)

    def get_columns_names(self):
        columns = []
        if self.report_id.report_type == 'date_range_extended':
            columns += [_('Non-issued')]
        if self.report_id.debit_credit and not self.comparison:
            columns += [_('Debit'), _('Credit')]
        columns += [self.get_balance_date()]
        if self.comparison:
            if self.periods_number == 1 or self.date_filter_cmp == 'custom':
                columns += [self.get_cmp_date(), '%']
            else:
                columns += self.get_cmp_periods(display=True)
        if self.report_id.report_type == 'date_range_extended':
            columns += [_('Older'), _('Total')]
        return columns

    @api.multi
    def get_columns_types(self):
        types = []
        if self.report_id.report_type == 'date_range_extended':
            types += ['number']
        if self.report_id.debit_credit and not self.comparison:
            types += ['number', 'number']
        types += ['number']
        if self.comparison:
            if self.periods_number == 1 or self.date_filter_cmp == 'custom':
                types += ['number', 'number']
            else:
                types += ['number' for k in xrange(self.periods_number)]
        if self.report_id.report_type == 'date_range_extended':
            types += ['number', 'number']
        return types

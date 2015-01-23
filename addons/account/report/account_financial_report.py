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

from openerp import models, fields, api
from openerp.tools.safe_eval import safe_eval
from openerp.tools.misc import formatLang
from datetime import timedelta, datetime
import calendar


class FormulaLine(object):
    def __init__(self, obj, type='balance'):
        fields = dict((fn, 0.0) for fn in ['balance', 'credit', 'debit'])
        if type == 'balance':
            fields = obj.get_balance()[0]
        elif type == 'sum':
            if obj._name == 'account.financial.report.line':
                fields = obj.get_sum()
            elif obj._name == 'account.move.line':
                field_names = ['balance', 'credit', 'debit']
                res = obj.compute_fields(field_names)
                if res.get(obj.id):
                    for field in field_names:
                        fields[field] = res[obj.id][field]
        self.balance = fields['balance']
        self.credit = fields['credit']
        self.debit = fields['debit']


class FormulaContext(dict):
    def __init__(self, reportLineObj, curObj, *data):
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


def report_safe_eval(expr, globals_dict=None, locals_dict=None, mode="eval", nocopy=False, locals_builtins=False):
    try:
        res = safe_eval(expr, globals_dict, locals_dict, mode, nocopy, locals_builtins)
    except ValueError:
        res = 1
    return res


class report_account_financial_report(models.Model):
    _name = "account.financial.report"
    _description = "Account Report"

    name = fields.Char()
    debit_credit = fields.Boolean('Show Credit and Debit Columns')
    line = fields.Many2one('account.financial.report.line', 'First/Top Line')
    offset_level = fields.Integer('Level at which the report starts', default=0)
    report_type = fields.Selection([('date_range', 'Based on date ranges'),
                                    ('date_range_extended', "Based on date ranges with 'older' and 'total' columns and last 3 months"),
                                    ('no_date_range', 'Based on a single date')],
                                   string='Not a date range report', default=False, required=True,
                                   help='For report like the balance sheet that do not work with date ranges')

    @api.multi
    def get_lines(self, context_id, line_id=None):
        if isinstance(context_id, int):
            context_id = self.env['account.financial.report.context'].browse(context_id)
        line_obj = self.line
        if line_id:
            line_obj = self.env['account.financial.report.line'].search([('id', '=', line_id)])
        if context_id.comparison:
            line_obj = line_obj.with_context(periods=context_id.get_cmp_periods())
        return line_obj.with_context(
            date_from=context_id.date_from,
            date_to=context_id.date_to,
            target_move=context_id.all_entries and 'all' or 'posted',
            unfolded_lines=context_id.unfolded_lines.ids,
            comparison=context_id.comparison,
            date_from_cmp=context_id.date_from_cmp,
            date_to_cmp=context_id.date_to_cmp,
            cash_basis=context_id.cash_basis,
            level=self.offset_level,
            periods_number=context_id.periods_number,
            context_id=context_id,
        ).get_lines(self)[0]

    def get_title(self):
        return self.name

    def get_name(self):
        return 'financial_report'

    def get_report_type(self):
        return self.report_type

    def get_template(self):
        return 'account.report_financial'


class account_financial_report_line(models.Model):
    _name = "account.financial.report.line"
    _description = "Account Report Line"
    _order = "sequence"

    name = fields.Char('Line Name')
    code = fields.Char('Line Code')
    parent_ids = fields.Many2many('account.financial.report.line', 'parent_financial_report_lines',
                                  'parent_id', 'child_id', string='Parents')
    children_ids = fields.Many2many('account.financial.report.line', 'parent_financial_report_lines',
                                    'child_id', 'parent_id', string='Children')
    financial_report = fields.Many2one('account.financial.report', 'Financial Report')
    sequence = fields.Integer('Sequence')
    domain = fields.Char('Domain', default=None)
    formulas = fields.Char('Formulas')
    groupby = fields.Char('Group By', default=False)
    foldable = fields.Boolean('Is the domain foldable', default=True)
    figure_type = fields.Selection([('float', 'Float'), ('percents', 'Percents'), ('no_unit', 'No Unit')],
                                   'Type of the figure', default='float', required=True)
    closing_balance = fields.Boolean('Closing balance', default=False, required=True)
    opening_year_balance = fields.Boolean('Opening year balance', default=False, required=True)
    hidden = fields.Boolean('Should this line be hidden', default=False, required=True)
    show_domain = fields.Boolean('Show the domain', default=True, required=True)
    green_on_positive = fields.Boolean('Is growth good when positive', default=True)

    @api.model
    def _ids_to_sql(self, ids):
        if len(ids) == 0:
            return '()'
        if len(ids) == 1:
            return '(' + str(ids[0]) + ')'
        return str(tuple(ids))

    def get_sum(self, field_names=None):
        ''' Returns the sum of the amls in the domain '''
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        if self.domain:
            amls = self.env['account.move.line'].search(report_safe_eval(self.domain))
            compute = amls.compute_fields(field_names)
            for aml in amls:
                if compute.get(aml.id):
                    for field in field_names:
                        res[field] += compute[aml.id][field]
        return res

    @api.one
    def get_balance(self, field_names=None):
        if not field_names:
            field_names = ['balance', 'credit', 'debit']
        res = dict((fn, 0.0) for fn in field_names)
        c = FormulaContext(self.env['account.financial.report.line'], self)
        if self.formulas:
            for f in self.formulas.split(';'):
                [field, formula] = f.split('=')
                field = field.strip()
                if field in field_names:
                    res[field] = report_safe_eval(formula, c, nocopy=True)
        return res

    def _format(self, value):
        if self.env.context.get('no_format'):
            return round(value, 1)
        if self.figure_type == 'float':
            currency_id = self.env.user.company_id.currency_id
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
            res = round(balance/comp * 100, 1)
        elif balance >= 0:
            res = 100.0
        else:
            res = -100.0
        if (res > 0) != self.green_on_positive:
            return (str(res) + '%', 'color: red;')
        else:
            return (str(res) + '%', 'color: green;')

    def _get_unfold(self, financial_report_id):
        if not self.foldable:
            return[True, False]
        currency_id = self.env.user.company_id.currency_id
        context = self.env.context
        unfolded = self.id in context['unfolded_lines']
        if unfolded:
            unfoldable = True
        elif not (self.domain and self.show_domain):
            unfoldable = False
        else:
            aml_obj = self.env['account.move.line']
            amls = aml_obj.search(report_safe_eval(self.domain))
            unfoldable = False
            if self.groupby and amls:
                select = ',COALESCE(SUM(l.debit-l.credit), 0)'
                if financial_report_id.debit_credit and not context['comparison']:
                    select += ',SUM(l.credit),SUM(l.debit)'
                sql = "SELECT l." + self.groupby + "%s FROM account_move_line l WHERE %s AND l.id IN %s GROUP BY l." + self.groupby
                query = sql % (select, amls._query_get(), self._ids_to_sql(amls.ids))
                self.env.cr.execute(query)
                gbs = self.env.cr.fetchall()
                for gb in gbs:
                    for k in gb[1:]:
                        if not currency_id.is_zero(k):
                            unfoldable = True
                if context['comparison']:
                    aml_cmp_obj = aml_obj.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])
                    aml_cmp_ids = aml_cmp_obj.search(report_safe_eval(self.domain))
                    if aml_cmp_ids:
                        select = ',COALESCE(SUM(l.debit-l.credit), 0)'
                        query = sql % (select, aml_cmp_ids._query_get(), self._ids_to_sql(aml_cmp_ids.ids))
                        self.env.cr.execute(query)
                        gbs_cmp = self.env.cr.fetchall()
                        for gb_cmp in gbs_cmp:
                            if not currency_id.is_zero(gb_cmp[1]):
                                unfoldable = True
            else:
                columns = ['balance']
                if financial_report_id.debit_credit and not context['comparison']:
                    if not context.get('cash_basis'):
                        columns += ['credit', 'debit']
                    else:
                        columns += ['credit_cash_basis', 'debit_cash_basis']
                results = amls.compute_fields(columns)
                if results:
                    for key, res in results.items():
                        for fn, value in res.items():
                            if not currency_id.is_zero(value):
                                unfoldable = True
                if context['comparison']:
                    aml_cmp_obj = aml_obj.with_context(date_from=context['date_from_cmp'], date_to=context['date_to_cmp'])
                    aml_cmp_ids = aml_cmp_obj.search(report_safe_eval(self.domain))
                    results = aml_cmp_ids.compute_fields(columns)
                    for res in results:
                        for field in res:
                            if not currency_id.is_zero(field):
                                unfoldable = True
        return [unfolded, unfoldable]

    def _put_columns_together(self, vals):
        columns = []
        if 'non_issued' in vals:
            columns += [vals['non_issued']]
        if 'debit' in vals and 'credit' in vals:
            columns += [vals['debit'], vals['credit']]
        if 'balance' in vals:
            columns += [vals['balance']]
        else:
            columns += ['']
        if self.env.context['comparison']:
            if self.env.context['periods_number'] == 1:
                columns += [vals.get('comparison', [''])[0], vals.get('comparison_pc', '')]
            else:
                if 'comparison' in vals:
                    columns += vals['comparison']
                for k in xrange(0, self.env.context['periods_number'] - len(vals.get('comparison', []))):
                    columns += ['']
        if 'older' in vals and 'total' in vals:
            columns += [vals['older'], vals['total']]
        vals['columns'] = columns
        return vals

    def _get_footnotes(self, type, target_id):
        footnotes = self.env.context['context_id'].footnotes.filtered(lambda s: s.type == type and s.target_id == target_id)
        result = {}
        for footnote in footnotes:
            result.update({footnote.column: footnote.number})
        return result

    @api.one
    def get_lines(self, financial_report_id):
        extended = False
        if financial_report_id.report_type == 'date_range_extended':
            extended = True
        lines = []
        context = self.env.context
        level = context['level']
        currency_id = self.env.user.company_id.currency_id
        if self.closing_balance or financial_report_id.report_type == 'no_date_range':
            self = self.with_context(closing_bal=True)
        if self.opening_year_balance:
            self = self.with_context(opening_year_bal=True)

        # Computing the lines
        vals = {
            'id': self.id,
            'name': self.name,
            'type': 'line',
            'level': level,
            'footnotes': self._get_footnotes('line', self.id),
        }
        [vals['unfolded'], vals['unfoldable']] = self._get_unfold(financial_report_id)

        # listing the columns
        columns = ['balance']
        if financial_report_id.debit_credit and not context['comparison']:
            if not context.get('cash_basis'):
                columns += ['credit', 'debit']
            else:
                columns += ['credit_cash_basis', 'debit_cash_basis']

        # computing the values for the lines
        total = 0
        if self.formulas:
            for key, value in self.get_balance(columns)[0].items():
                vals[key] = self._format(value)
                if key == 'balance':
                    balance = value
                    total += balance
            if context['comparison']:
                vals['comparison'] = []
                periods = context['periods']
                for period in periods:
                    cmp_line = self.with_context(date_from=period[0], date_to=period[1])
                    value = cmp_line.get_balance(['balance'])[0]['balance']
                    vals['comparison'].append(self._format(value))
                    total += value
                    if context['periods_number'] == 1:
                        vals['comparison_pc'] = self._build_cmp(balance, value)
            if extended:
                if context['comparison']:
                    older_date_to = periods[-1][0]
                else:
                    older_date_to = context['date_from']
                older_line = self.with_context(closing_bal=True, date_to=older_date_to)
                value = older_line.get_balance(['balance'])[0]['balance']
                vals['older'] = self._format(value)
                total += value
                non_issued_line = self.with_context(non_issued=True)
                value = non_issued_line.get_balance(['balance'])[0]['balance']
                vals['non_issued'] = self._format(value)
                total += value
                vals['total'] = self._format(total)
        if not self.hidden:
            vals = self._put_columns_together(vals)
            lines.append(vals)

        # if the line has a domain, computing its values
        if self.domain and vals['unfolded'] and self.groupby and self.show_domain:
            aml_obj = self.env['account.move.line']
            amls = aml_obj.search(report_safe_eval(self.domain))

            if self.groupby:
                if len(amls) > 0:
                    select = ',COALESCE(SUM(l.debit-l.credit), 0)'
                    if financial_report_id.debit_credit and not context['comparison']:
                        select += ',SUM(l.credit),SUM(l.debit)'
                    sql = "SELECT l." + self.groupby + "%s FROM account_move_line l WHERE %s AND l.id IN %s GROUP BY l." + self.groupby
                    query = sql % (select, amls._query_get(), self._ids_to_sql(amls.ids))
                    self.env.cr.execute(query)
                    gbs = self.env.cr.fetchall()
                    gbs_cmp = []
                    if context['comparison']:
                        periods = context['periods']
                        for period in periods:
                            aml_cmp_obj = aml_obj.with_context(date_from=period[0], date_to=period[1])
                            aml_cmp_ids = aml_cmp_obj.search(report_safe_eval(self.domain))
                            select = ',COALESCE(SUM(l.debit-l.credit), 0)'
                            query = sql % (select, aml_cmp_ids._query_get(), self._ids_to_sql(aml_cmp_ids.ids))
                            self.env.cr.execute(query)
                            gbs_cmp.append(dict(self.env.cr.fetchall()))
                    if extended:
                        aml_older_obj = aml_obj.with_context(closing_bal=True, date_to=older_date_to)
                        aml_older_ids = aml_older_obj.search(report_safe_eval(self.domain))
                        select = ',COALESCE(SUM(l.debit-l.credit), 0)'
                        query = sql % (select, aml_older_ids._query_get(), self._ids_to_sql(aml_older_ids.ids))
                        self.env.cr.execute(query)
                        gb_older = dict(self.env.cr.fetchall())
                        aml_non_issued_obj = aml_obj.with_context(non_issued=True)
                        aml_non_issued_ids = aml_non_issued_obj.search(report_safe_eval(self.domain))
                        query = sql % (select, aml_non_issued_ids._query_get(), self._ids_to_sql(aml_non_issued_ids.ids))
                        self.env.cr.execute(query)
                        gb_non_issued = dict(self.env.cr.fetchall())

                    for gb in gbs:
                        vals = {'id': gb[0], 'name': self._get_gb_name(gb[0]), 'level': level + 2, 
                                'type': self.groupby, 'footnotes': self._get_footnotes(self.groupby, gb[0])}
                        total = 0
                        flag = False
                        for column in xrange(1, len(columns) + 1):
                            value = gb[column]
                            vals[columns[column - 1]] = self._format(value)
                            if columns[column - 1] == 'balance':
                                total += value
                            if not currency_id.is_zero(value):
                                flag = True
                        if context['comparison']:
                            vals['comparison'] = []
                            for gb_cmp in gbs_cmp:
                                if gb_cmp.get(gb[0]):
                                    vals['comparison'].append(self._format(gb_cmp[gb[0]]))
                                    total += gb_cmp[gb[0]]
                                    if not currency_id.is_zero(gb_cmp[gb[0]]):
                                        flag = True
                                    del gb_cmp[gb[0]]
                                else:
                                    vals['comparison'].append(self._format(0))
                                if context['periods_number'] == 1:
                                    vals['comparison_pc'] = self._build_cmp(gb[1], gb_cmp.get(gb[0], 0))
                        if extended:
                            if gb_older.get(gb[0]):
                                vals['older'] = self._format(gb_older[gb[0]])
                                total += gb_older[gb[0]]
                                if not currency_id.is_zero(gb_older[gb[0]]):
                                    flag = True
                                del gb_older[gb[0]]
                            else:
                                vals['older'] = self._format(0)
                            if gb_non_issued.get(gb[0]):
                                vals['non_issued'] = self._format(gb_non_issued[gb[0]])
                                total += gb_non_issued[gb[0]]
                                if not currency_id.is_zero(gb_non_issued[gb[0]]):
                                    flag = True
                                del gb_non_issued[gb[0]]
                            else:
                                vals['non_issued'] = self._format(0)
                            vals['total'] = self._format(total)
                        if flag:
                            vals = self._put_columns_together(vals)
                            lines.append(vals)

                    if gbs_cmp or (extended and (gb_older or gb_non_issued)):
                        extra_gbs = []
                        for gb_cmp in gbs_cmp:
                            for key, value in gb_cmp.items() + (extended and gb_older.items() or []):
                                if key not in extra_gbs:
                                    extra_gbs.append(key)
                        for extra_gb in extra_gbs:
                            total = 0
                            vals = {'id': extra_gb, 'name': self._get_gb_name(extra_gb), 'level': level + 2, 'type': self.groupby,
                                    'balance': self._format(0), 'comparison': [], 'footnotes': self._get_footnotes(self.groupby, extra_gb)}
                            for gb_cmp in gbs_cmp:
                                if extra_gb in gb_cmp:
                                    vals['comparison'].append(self._format(gb_cmp[extra_gb]))
                                    total += gb_cmp[extra_gb]
                                else:
                                    vals['comparison'].append(self._format(0))
                                if context['periods_number'] == 1:
                                    vals['comparison_pc'] = self._build_cmp(0, gb_cmp.get(extra_gb, 0))
                            if extended:
                                if extra_gb in gb_older:
                                    vals['older'] = self._format(gb_older[extra_gb])
                                    total += gb_older[extra_gb]
                                else:
                                    vals['older'] = self._format(0)
                                if extra_gb in gb_non_issued:
                                    vals['non_issued'] = self._format(gb_non_issued[extra_gb])
                                    total += gb_non_issued[extra_gb]
                                else:
                                    vals['non_issued'] = self._format(0)
                                vals['total'] = self._format(total)
                            vals = self._put_columns_together(vals)
                            lines.append(vals)

            else:
                for aml in amls:
                    vals = {'id': aml.id, 'name': aml.name, 'type': 'aml', 'level': level + 2, 'footnotes': self._get_footnotes('aml', aml.id)}
                    c = FormulaContext(self.env['account.financial.report.line'], aml)
                    flag = False
                    if self.formulas:
                        for f in self.formulas.split(';'):
                            [column, formula] = f.split('=')
                            column = column.strip()
                            if column in columns:
                                value = report_safe_eval(formula, c, nocopy=True)
                                vals[column] = self._format(value)
                                if column == 'balance':
                                    balance = value
                                if not aml.company_id.currency_id.is_zero(value):
                                    flag = True
                            if column == 'balance':
                                if context['comparison']:
                                    periods = context['periods']
                                    vals['comparison'] = []
                                    for period in periods:
                                        aml_cmp_obj = aml_obj.with_context(date_from=period[0], date_to=period[1])
                                        c_cmp = FormulaContext(self.env['account.financial.report.line'], aml_cmp_obj.browse(aml.id))
                                        value = report_safe_eval(formula, c_cmp, nocopy=True)
                                        vals['comparison'].append(self._format(value))
                                        if not aml.company_id.currency_id.is_zero(value):
                                            flag = True
                                        if context['periods_number'] == 1:
                                            vals['comparison_pc'] = self._build_cmp(balance, value)
                                if extended:
                                    aml_older_obj = aml_obj.with_context(closing_bal=True, date_to=older_date_to)
                                    c_older = FormulaContext(self.env['account.financial.report.line'], aml_older_obj.browse(aml.id))
                                    value = report_safe_eval(formula, c_older, nocopy=True)
                                    vals['older'] = self._format(value)
                                    total += value
                                    if not aml.company_id.currency_id.is_zero(value):
                                        flag = True
                                    aml_non_issued_obj = aml_obj.with_context(non_issued=True)
                                    c_non_issued = FormulaContext(self.env['account.financial.report.line'], aml_non_issued_obj.browse(aml.id))
                                    value = report_safe_eval(formula, c_non_issued, nocopy=True)
                                    vals['non_issued'] = self._format(value)
                                    total += value
                                    vals['total'] = self._format(total)
                                    if not aml.company_id.currency_id.is_zero(value):
                                        flag = True
                    if flag:
                        vals = self._put_columns_together(vals)
                        lines.append(vals)

        new_lines = self.children_ids.with_context(level=level+1).get_lines(financial_report_id)
        result = []
        if level > 0:
            result += lines
        for new_line in new_lines:
            result += new_line
        if level <= 0:
            result += lines
        return result


class account_financial_report_context(models.TransientModel):
    _name = "account.financial.report.context"
    _description = "A particular context for a financial report"
    _inherit = "account.report.context.common"

    def get_report_obj(self):
        return self.report_id

    report_id = fields.Many2one('account.financial.report', 'Linked financial report', help='Only if financial report')
    unfolded_lines = fields.Many2many('account.financial.report.line', 'context_to_line', string='Unfolded lines')
    footnotes = fields.Many2many('account.report.footnote', 'account_context_footnote_financial', string='Footnotes')

    @api.multi
    def add_footnote(self, type, target_id, column, number, text):
        footnote = self.env['account.report.footnote'].create(
            {'type': type, 'target_id': target_id, 'column': column, 'number': number, 'text': text}
        )
        self.write({'footnotes': [(4, footnote.id)]})

    @api.multi
    def edit_footnote(self, number, text):
        footnote = self.footnotes.filtered(lambda s: s.number == number)
        footnote.write({'text': text})

    @api.multi
    def remove_footnote(self, number):
        footnotes = self.footnotes.filtered(lambda s: s.number == number)
        self.write({'footnotes': [(3, footnotes.id)]})

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
            columns += ['Non-issued']
        if self.report_id.debit_credit and not self.comparison:
            columns += ['Debit', 'Credit']
        columns += [self.get_balance_date()]
        if self.comparison:
            if self.periods_number == 1 or self.date_filter_cmp == 'custom':
                columns += [self.get_cmp_date(), '%']
            else:
                columns += self.get_cmp_periods(display=True)
        if self.report_id.report_type == 'date_range_extended':
            columns += ['Older', 'Total']
        return columns

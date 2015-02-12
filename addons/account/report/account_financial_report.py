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
        elif type == 'not_computed':
            for field in fields:
                fields[field] = obj.get(field, 0)
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
    line_ids = fields.One2many('account.financial.report.line', 'financial_report_id', string='Lines')
    report_type = fields.Selection([('date_range', 'Based on date ranges'),
                                    ('date_range_extended', "Based on date ranges with 'older' and 'total' columns and last 3 months"),
                                    ('no_date_range', 'Based on a single date')],
                                   string='Not a date range report', default=False, required=True,
                                   help='For report like the balance sheet that do not work with date ranges')


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
            cash_basis=context_id.cash_basis,
        ).get_lines(self, context_id)
        return res

    def get_title(self):
        return self.name

    def get_name(self):
        return 'financial_report'

    def get_report_type(self):
        return self.report_type


class account_financial_report_line(models.Model):
    _name = "account.financial.report.line"
    _description = "Account Report Line"
    _order = "sequence"

    name = fields.Char('Line Name')
    code = fields.Char('Line Code')
    financial_report_id = fields.Many2one('account.financial.report', 'Financial Report')
    parent_id = fields.Many2one('account.financial.report.line', string='Parent')
    children_ids = fields.One2many('account.financial.report.line', 'parent_id', string='Children')
    sequence = fields.Integer('Sequence')

    domain = fields.Char('Domain', default=None)
    formulas = fields.Char('Formulas')
    groupby = fields.Char('Group By', default=False)
    figure_type = fields.Selection([('float', 'Float'), ('percents', 'Percents'), ('no_unit', 'No Unit')],
                                   'Type of the figure', default='float', required=True)
    green_on_positive = fields.Boolean('Is growth good when positive', default=True)
    level = fields.Integer(required=True)
    special_date_changer = fields.Selection([('from_beginning', 'From the beginning'), ('to_beginning_of_fy', 'At the beginning of the Year'), ('normal', 'Use given dates')], default='normal')
    show_domain = fields.Selection([('always', 'Always'), ('never', 'Never'), ('foldable', 'Foldable')], default='foldable')

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
            res = round(balance/comp * 100, 1)
        elif balance >= 0:
            res = 100.0
        else:
            res = -100.0
        if (res > 0) != self.green_on_positive:
            return (str(res) + '%', 'color: red;')
        else:
            return (str(res) + '%', 'color: green;')

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
            select = ',COALESCE(SUM(\"account_move_line\".debit-\"account_move_line\".credit), 0)'
            if financial_report.debit_credit and debit_credit:
                select += ',SUM(\"account_move_line\".credit),SUM(\"account_move_line\".debit)'
            sql = "SELECT \"account_move_line\"." + groupby + "%s FROM \"account_move_line\" WHERE %s GROUP BY \"account_move_line\"." + groupby
            where_clause, where_params = aml_obj._query_get(domain=self.domain)
            query = sql % (select, where_clause)
            self.env.cr.execute(query, where_params)
            results = self.env.cr.fetchall()
            if financial_report.debit_credit and debit_credit:
                results = dict([(k[0], {'balance': k[1], 'credit': k[2], 'debit': k[3]}) for k in results])
            else:
                results = dict([(k[0], {'balance': k[1]}) for k in results])
            c = FormulaContext(self.env['account.financial.report.line'])
            if formulas:
                for key in results:
                    c['sum'] = FormulaLine(results[key], type='not_computed')
                    for col, formula in formulas.items():
                        if col in results[key]:
                            results[key][col] = report_safe_eval(formula, c, nocopy=True)

        results.update({'line': vals})

        return results

    @api.multi
    def get_lines(self, financial_report, context):
        final_result_table = []
        comparison_table = context.get_periods()
        #build comparison table

        for line in self:
            line_comparison_table = comparison_table
            if line.special_date_changer == 'from_beginning':
                line_comparison_table = [(False, k[1]) for k in comparison_table]
            if line.special_date_changer == 'to_begining_of_fy':
                for period in line_comparison_table:
                    date_to = datetime.strptime(period[1], "%Y-%m-%d")
                    period[1] = date_to.strftime('%Y-01-01')
            res = []
            debit_credit = len(comparison_table) == 1
            domain_ids = {'line'}
            for period in line_comparison_table:
                r = line.with_context(date_from=period[0], date_to=period[1]).eval_formula(financial_report, debit_credit, context)
                debit_credit = False
                res.append(r)
                domain_ids.update(set(r.keys()))

            # Post-processing ; creating line dictionnary, building comparison, computing total for extended, formatting
            vals = {
                'id': line.id,
                'name': line.name,
                'type': 'line',
                'level': line.level,
                'footnotes': line._get_footnotes('line', line.id, context),
                'columns': sum([[j[1] for j in k['line'].items()] for k in res], []),
                'unfoldable': len(domain_ids) > 1 and line.show_domain != 'always',
                'unfolded': line in context.unfolded_lines or line.show_domain == 'always',
            }
            domain_ids.remove('line')
            lines = [vals]
            groupby = line.groupby or 'aml'
            if line in context.unfolded_lines:# or line.show_domain == 'always':
                for domain_id in domain_ids:
                    vals = {
                        'id': domain_id,
                        'name': line._get_gb_name(domain_id),
                        'level': line.level + 2,
                        'type': groupby,
                        'footnotes': line._get_footnotes(groupby, domain_id, context),
                        'columns': sum([[j[1] for j in k.get(domain_id, dict([(l, 0) for l in k['line'].keys()])).items()] for k in res], []),
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

            new_lines = line.children_ids.get_lines(financial_report, context)

            result = []
            if line.level > 0:
                result += lines
            result += new_lines
            if line.level <= 0:
                result += lines
            final_result_table += result

        return final_result_table


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
    def render_html(self, data=None):
        report_obj = self.env['report']
        module_report = report_obj._get_report_from_name('account.report_financial')
        docargs = {
            'doc_ids': self.ids,
            'doc_model': module_report.model,
            'docs': self,
            'data': data,
            'get_start_date': self._get_start_date,
            'get_end_date': self._get_end_date,
            'get_account': self._get_account,
            'get_fiscalyear': self._get_fiscalyear,
            'get_target_move': self._get_target_move,
            'get_lines': self._get_lines
        }
        return report_obj.render('account.report_financial', docargs)


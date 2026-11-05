from dateutil.relativedelta import relativedelta

from odoo import fields, models


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _l10n_az_tit_month_income(self, options, month_index):
        """ Return the income recognised during one month of the reporting quarter.

        :param options: the report options; the quarter is the one containing
                        options['date']['date_to'].
        :param month_index: the month of the quarter to compute (1, 2 or 3).
        :return: the negated sum of balances of posted move lines booked on
                 'income' accounts of the current company during that month.
        """
        date_to = fields.Date.to_date(options['date']['date_to'])
        quarter_start = date_to.replace(month=(date_to.month - 1) // 3 * 3 + 1, day=1)
        month_start = quarter_start + relativedelta(months=month_index - 1)
        month_end = month_start + relativedelta(months=1, days=-1)
        [(balance,)] = self.env['account.move.line']._read_group(
            domain=[
                ('company_id', '=', self.env.company.id),
                ('parent_state', '=', 'posted'),
                ('account_id.account_type', '=', 'income'),
                ('date', '>=', month_start),
                ('date', '<=', month_end),
            ],
            aggregates=['balance:sum'],
        )
        return -(balance or 0.0)

    def _l10n_az_tit_month_engine_result(self, options, month_index, formulas_dict, current_groupby):
        """ Wrap _l10n_az_tit_month_income following the report engine result convention. """
        result = self._l10n_az_tit_month_income(options, month_index)
        return {
            expression: [] if current_groupby else {'result': result, 'has_sublines': False}
            for expressions in formulas_dict.values()
            for expression in expressions
        }

    def _report_engine_l10n_az_tit_month1(self, options, date_scope, formulas_dict, current_groupby, warnings=None):
        return self._l10n_az_tit_month_engine_result(options, 1, formulas_dict, current_groupby)

    def _report_engine_l10n_az_tit_month2(self, options, date_scope, formulas_dict, current_groupby, warnings=None):
        return self._l10n_az_tit_month_engine_result(options, 2, formulas_dict, current_groupby)

    def _report_engine_l10n_az_tit_month3(self, options, date_scope, formulas_dict, current_groupby, warnings=None):
        return self._l10n_az_tit_month_engine_result(options, 3, formulas_dict, current_groupby)

    def _report_engine_l10n_az_tit_rate(self, options, date_scope, formulas_dict, current_groupby, warnings=None):
        """ Return the simplified tax rate (%), set by the 'l10n_az.simplified_tax_rate' system parameter. """
        result = self.env['ir.config_parameter'].sudo().get_float('l10n_az.simplified_tax_rate', 2.0)
        return {
            expression: [] if current_groupby else {'result': result, 'has_sublines': False}
            for expressions in formulas_dict.values()
            for expression in expressions
        }

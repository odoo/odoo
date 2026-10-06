from odoo import models


class AccountReport(models.Model):
    _inherit = 'account.report'

    def _report_engine_l10n_uz_turnover_rate(self, options, date_scope, formulas_dict, current_groupby, warnings=None):
        """ Return the turnover tax rate (%), set by the 'l10n_uz.turnover_tax_rate' system parameter. """
        result = self.env['ir.config_parameter'].sudo().get_float('l10n_uz.turnover_tax_rate', 4.0)
        return {
            expression: [] if current_groupby else {'result': result, 'has_sublines': False}
            for expressions in formulas_dict.values()
            for expression in expressions
        }

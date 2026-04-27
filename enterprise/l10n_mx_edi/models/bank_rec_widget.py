from odoo import models


class BankRecWidget(models.Model):
    _inherit = 'bank.rec.widget'

    def _line_value_changed_l10n_mx_edi_payment_method_id(self, line):
        self.ensure_one()
        if line.flag == 'liquidity' and line.l10n_mx_edi_payment_method_id:
            self.st_line_id.l10n_mx_edi_payment_method_id = line.l10n_mx_edi_payment_method_id
            self._action_reload_liquidity_line()

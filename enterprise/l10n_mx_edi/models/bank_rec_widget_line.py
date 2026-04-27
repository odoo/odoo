from odoo import fields, models


class BankRecWidgetLine(models.Model):
    _inherit = 'bank.rec.widget.line'

    l10n_mx_edi_payment_method_id = fields.Many2one(
        comodel_name='l10n_mx_edi.payment.method',
        compute='_compute_l10n_mx_edi_payment_method_id',
        store=True,
    )

    def _compute_l10n_mx_edi_payment_method_id(self):
        for line in self:
            if line.flag == 'liquidity':
                line.l10n_mx_edi_payment_method_id = line.wizard_id.st_line_id.l10n_mx_edi_payment_method_id

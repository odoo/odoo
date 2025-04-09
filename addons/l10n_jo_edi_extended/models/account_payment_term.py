from odoo import api, fields, models


class PaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    enable_l10n_jo_edi_cash_payment_method = fields.Boolean(compute='_compute_l10n_jo_edi_cash_payment_method_fields')
    l10n_jo_edi_cash_payment_method = fields.Boolean(
        string="JoFotara Cash Payment Method",
        compute='_compute_l10n_jo_edi_cash_payment_method_fields',
        store=True, readonly=False,
    )

    @api.depends('line_ids')
    def _compute_l10n_jo_edi_cash_payment_method_fields(self):
        for term in self:
            term.enable_l10n_jo_edi_cash_payment_method = len(term.line_ids) == 1 \
                and term.line_ids[0].value == 'percent' \
                and term.line_ids[0].value_amount == 100 \
                and term.line_ids[0].delay_type == 'days_after' \
                and term.line_ids[0].nb_days == 0
            if not term.enable_l10n_jo_edi_cash_payment_method:
                term.l10n_jo_edi_cash_payment_method = False

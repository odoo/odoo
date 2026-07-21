from odoo import api, fields, models


class PosPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])
    l10n_jo_edi_pos_is_cash = fields.Boolean(
        string="JoFotara Cash",
        help="If checked, this payment method will reported as a cash payment method to JoFotara.",
        compute='_compute_l10n_jo_edi_pos_is_cash',
        store=True, readonly=False,
    )

    @api.depends('journal_id.type')
    def _compute_l10n_jo_edi_pos_is_cash(self):
        for pm in self:
            pm.l10n_jo_edi_pos_is_cash = pm.journal_id.type == 'cash'

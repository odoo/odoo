from odoo import api, fields, models

from odoo.addons.l10n_pt_certification.models.account_payment_method import L10N_PT_PAYMENT_MECHANISMS


class PoSPaymentMethod(models.Model):
    _inherit = 'pos.payment.method'

    l10n_pt_pos_payment_mechanism = fields.Selection(
        selection=L10N_PT_PAYMENT_MECHANISMS,
        string='Payment Mechanism',
        compute='_compute_l10n_pt_pos_payment_mechanism',
        store=True,
        readonly=False,
        help="This payment method's mechanism according to Portuguese requirements.",
    )
    country_code = fields.Char(related='company_id.country_id.code', depends=['company_id.country_id'])

    @api.depends('is_cash_count', 'country_code')
    def _compute_l10n_pt_pos_payment_mechanism(self):
        # Default payment mechanism for cash to 'NU' (Numerário = Cash)
        for payment_method in self:
            if payment_method.is_cash_count and payment_method.country_code == 'PT':
                payment_method.l10n_pt_pos_payment_mechanism = 'NU'
            else:
                payment_method.l10n_pt_pos_payment_mechanism = None

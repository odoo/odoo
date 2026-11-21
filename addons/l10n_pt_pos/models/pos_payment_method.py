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

    @api.depends('is_cash_count', 'company_id.account_fiscal_country_id')
    def _compute_l10n_pt_pos_payment_mechanism(self):
        # A PT cash method is paid in cash, 'NU' (numerário). A mechanism chosen by hand is kept, but not
        # 'NU' once the method no longer counts cash.
        for payment_method in self:
            mechanism = payment_method.l10n_pt_pos_payment_mechanism
            if (
                payment_method.is_cash_count and not mechanism
                and payment_method.company_id.account_fiscal_country_id.code == 'PT'
            ):
                mechanism = 'NU'
            elif not payment_method.is_cash_count and mechanism == 'NU':
                mechanism = False
            payment_method.l10n_pt_pos_payment_mechanism = mechanism

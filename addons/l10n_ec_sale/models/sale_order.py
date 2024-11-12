from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    l10n_ec_sri_payment_id = fields.Many2one(
        comodel_name="l10n_ec.sri.payment",
        string="Payment Method (SRI)",
        help="Ecuador: Payment Methods Defined by the SRI.",
        default=lambda self: self.env['l10n_ec.sri.payment'].search([], limit=1),
    )

    def _prepare_invoice(self):
        res = super()._prepare_invoice()
        if self.country_code == 'EC':
            res['l10n_ec_sri_payment_id'] = self.l10n_ec_sri_payment_id.id
        return res

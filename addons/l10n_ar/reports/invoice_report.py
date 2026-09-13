from odoo import fields, models
from odoo.tools import SQL


class AccountInvoiceReport(models.Model):
    _inherit = "account.invoice.report"

    l10n_ar_state_id = fields.Many2one(
        comodel_name="res.country.state",
        string="Delivery Province",
        readonly=True,
    )
    date = fields.Date(
        string="Accounting Date",
        readonly=True,
    )

    _depends = {
        "account.move": ["partner_shipping_id", "date"],
        "res.partner": ["state_id"],
    }

    def _select(self) -> SQL:
        return SQL(
            "%s, contact_partner.state_id as l10n_ar_state_id, move.date",
            super()._select(),
        )

    def _from(self) -> SQL:
        return SQL(
            "%s LEFT JOIN res_partner contact_partner ON contact_partner.id = COALESCE(move.partner_shipping_id, move.partner_id)",
            super()._from(),
        )

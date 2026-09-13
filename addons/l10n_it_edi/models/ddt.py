from odoo import api, fields, models


class L10n_ItDdt(models.Model):
    _name = "l10n_it.ddt"
    _description = "Transport Document"

    invoice_id = fields.One2many(
        comodel_name="account.move",
        inverse_name="l10n_it_ddt_id",
        string="Invoice Reference",
    )
    name = fields.Char(
        string="Numero DDT",
        size=20,
        required=True,
        help="Transport document number",
    )
    date = fields.Date(
        string="Data DDT",
        required=True,
        help="Transport document date",
    )

    @api.depends("date")
    def _compute_display_name(self):
        for ddt in self:
            ddt.display_name = f"{ddt.name} ({ddt.date})"

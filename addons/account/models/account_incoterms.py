from odoo import api, fields, models


class AccountIncoterms(models.Model):
    _name = "account.incoterms"
    _description = "Incoterms"

    name = fields.Char(
        help="Incoterms are series of sales terms. They are used to divide transaction costs and responsibilities between buyer and seller and reflect state-of-the-art transportation practices.",
        translate=True,
        required=True,
    )
    code = fields.Char(
        help="Incoterm Standard Code",
        size=3,
        required=True,
    )
    active = fields.Boolean(
        help="By unchecking the active field, you may hide an INCOTERM you will not use.",
        default=True,
    )

    @api.depends("code")
    def _compute_display_name(self):
        for incoterm in self:
            incoterm.display_name = "%s%s" % (
                (incoterm.code and "[%s] " % incoterm.code) or "",
                incoterm.name,
            )

from odoo import api, fields, models
from odoo.db.schema import column_exists, create_column


class ResPartner(models.Model):
    _inherit = "res.partner"

    l10n_gr_edi_branch_number = fields.Integer(
        string="Branch Number",
        compute="_compute_l10n_gr_edi_branch_number",
        store=True,
        readonly=False,
        help="Branch number in the Tax Registry",
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, "res_partner", "l10n_gr_edi_branch_number"):
            create_column(
                self.env.cr, "res_partner", "l10n_gr_edi_branch_number", "int4"
            )
        return super()._auto_init()

    @api.depends("country_code")
    def _compute_l10n_gr_edi_branch_number(self):
        for partner in self:
            if partner.country_code == "GR":
                partner.l10n_gr_edi_branch_number = (
                    partner.l10n_gr_edi_branch_number or 0
                )
            else:
                partner.l10n_gr_edi_branch_number = False

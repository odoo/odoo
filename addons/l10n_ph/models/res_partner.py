from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    branch_code = fields.Char(
        compute="_compute_branch_code",
        default="000",
        store=True,
    )
    first_name = fields.Char()
    middle_name = fields.Char()
    last_name = fields.Char()
    l10n_ph_rdo = fields.Char(
        string="RDO",
        help="Revenue District Office",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + ["branch_code"]

    @api.depends("vat", "country_id")
    def _compute_branch_code(self):
        for partner in self:
            branch_code = "000"
            if partner.country_id.code == "PH" and partner.vat:
                match = partner._check_vat_ph_re.match(partner.vat)
                branch_code = (
                    match and match.group(1) and match.group(1)[1:]
                ) or branch_code
            partner.branch_code = branch_code

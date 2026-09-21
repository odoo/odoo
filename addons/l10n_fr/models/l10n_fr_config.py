from odoo import api, fields, models


class L10nFrConfig(models.Model):
    _name = "l10n_fr.config"
    _description = "A company's l10n fr configuration"
    _inherit = ["mixin.company.config"]

    l10n_fr_closing_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Sequence to use to build sale closings",
        readonly=True,
    )
    ape = fields.Char(string="APE")
    is_france_country = fields.Boolean(
        string="Is Part of DOM-TOM",
        compute="_compute_is_france_country",
    )

    @api.depends("company_id.country_code")
    def _compute_is_france_country(self):
        for config in self:
            config.is_france_country = (
                config.company_id.country_code
                in self.env["res.company"]._get_france_country_codes()
            )

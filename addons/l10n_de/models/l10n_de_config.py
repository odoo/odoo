from odoo import api, fields, models


class L10nDeConfig(models.Model):
    _name = "l10n_de.config"
    _description = "A company's l10n de configuration"
    _inherit = ["mixin.company.config"]

    l10n_de_stnr = fields.Char(
        string="St.-Nr.",
        tracking=True,
        help="Tax number. Scheme: ??FF0BBBUUUUP, e.g.: 2893081508152 https://de.wikipedia.org/wiki/Steuernummer",
    )
    l10n_de_widnr = fields.Char(
        string="W-IdNr.",
        tracking=True,
        help="Business identification number.",
    )

    @api.constrains("company_id.state_id", "l10n_de_stnr")
    def _check_l10n_de_stnr(self):
        for config in self:
            config.company_id.get_l10n_de_stnr_national()

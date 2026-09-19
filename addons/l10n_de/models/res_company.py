import stdnum.de.stnr
import stdnum.exceptions

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = "res.company"

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

    @api.constrains("state_id", "l10n_de_stnr")
    def _check_l10n_de_stnr(self):
        for record in self:
            record.get_l10n_de_stnr_national()

    def get_l10n_de_stnr_national(self):
        self.check_singleton()
        national_steuer_nummer = None

        if self.l10n_de_stnr and self.country_code == "DE":
            try:
                national_steuer_nummer = stdnum.de.stnr.to_country_number(
                    self.l10n_de_stnr, self.state_id.name
                )
            except stdnum.exceptions.InvalidComponent:
                raise ValidationError(
                    _("Your company's SteuerNummer is not compatible with your state")
                )
            except stdnum.exceptions.InvalidFormat:
                if stdnum.de.stnr.is_valid(self.l10n_de_stnr, self.state_id.name):
                    national_steuer_nummer = self.l10n_de_stnr
                else:
                    raise ValidationError(_("Your company's SteuerNummer is not valid"))

        elif self.l10n_de_stnr:
            national_steuer_nummer = self.l10n_de_stnr

        return national_steuer_nummer

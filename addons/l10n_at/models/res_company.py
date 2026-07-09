import stdnum.at.tin
import stdnum.exceptions

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_at_stnr = fields.Char(
        string="St.-Nr. (AT)",
        help="Tax number (Steuernummer / Abgabenkontonummer). Scheme: FF-BBB/UUUUP, e.g.: 59-119/9013 https://de.wikipedia.org/wiki/Abgabenkontonummer",
        tracking=True,
    )

    @api.constrains('l10n_at_stnr')
    def _validate_l10n_at_stnr(self):
        for record in self:
            record.get_l10n_at_stnr_national()

    def get_l10n_at_stnr_national(self):
        self.ensure_one()
        if self.country_code != 'AT':
            return None

        if self.l10n_at_stnr:
            try:
                return stdnum.at.tin.validate(self.l10n_at_stnr)
            except stdnum.exceptions.ValidationError:
                raise ValidationError(_("Your company's SteuerNummer is not valid"))

        return None

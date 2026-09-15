import re

from odoo import api, fields, models


VAT_SIREN_RE = re.compile(r'FR[A-Z0-9]{2}([0-9]{9})', re.IGNORECASE)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_is_french = fields.Boolean(compute='_compute_l10n_fr_is_french')

    @api.depends('country_code')
    def _compute_l10n_fr_is_french(self):
        for partner in self:
            partner.l10n_fr_is_french = partner.country_code in self.env['res.company']._get_france_country_codes()

    def _l10n_fr_get_siren_from_vat(self):
        self.ensure_one()
        vat = (self.vat or '').replace(' ', '')
        match = VAT_SIREN_RE.fullmatch(vat)
        return match and match.group(1)

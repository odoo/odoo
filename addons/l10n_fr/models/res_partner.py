from stdnum.exceptions import ValidationError as StdnumValidationError
from stdnum.fr import siret

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_is_french = fields.Boolean(compute='_compute_l10n_fr_is_french')
    l10n_fr_siret_warning = fields.Char(compute='_compute_l10n_fr_siret_warning')

    @api.depends('country_code')
    def _compute_l10n_fr_is_french(self):
        for partner in self:
            partner.l10n_fr_is_french = partner.country_code in self.env['res.company']._get_france_country_codes()

    @api.depends('company_registry', 'l10n_fr_is_french')
    def _compute_l10n_fr_siret_warning(self):
        for partner in self:
            partner.l10n_fr_siret_warning = False
            if (not partner.company_registry or not partner.l10n_fr_is_french):
                continue

            try:
                siret.validate(partner.company_registry)
            except StdnumValidationError as e:
                partner.l10n_fr_siret_warning = self.env._(
                    "Invalid SIRET: %(error)s",
                    error=str(e),
                )

    def _get_company_registry_labels(self):
        labels = super()._get_company_registry_labels()
        labels['FR'] = self.env._("SIRET")
        return labels

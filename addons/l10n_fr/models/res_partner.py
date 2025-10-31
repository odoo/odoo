from odoo import _, api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_is_french = fields.Boolean(compute='_compute_l10n_fr_is_french')

    @api.depends('country_code')
    def _compute_l10n_fr_is_french(self):
        for partner in self:
            partner.l10n_fr_is_french = partner.country_code in self.env['res.company']._get_france_country_codes()

    def _get_company_registry_labels(self):
        labels = super()._get_company_registry_labels()
        for code in self.env['res.company']._get_france_country_codes():
            labels[code] = _("Siret")
        return labels

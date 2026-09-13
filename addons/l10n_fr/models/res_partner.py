from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_fr_trade_name = fields.Char(string='Trade Name')
    l10n_fr_ape = fields.Char(string='APE')
    l10n_fr_insee_commune_code = fields.Char(string='INSEE Commune Code')
    l10n_fr_legal_representative_name = fields.Char(string='Legal Representative')
    l10n_fr_legal_representative_role_code = fields.Char(string='Legal Representative Role Code')
    l10n_fr_main_activity = fields.Text(string='Main Activity')
    l10n_fr_legal_form_code = fields.Char(string='Legal Form Code')
    l10n_fr_creation_date = fields.Date(string='Creation Date')
    l10n_fr_is_french = fields.Boolean(compute='_compute_l10n_fr_is_french')

    @api.depends('country_code')
    def _compute_l10n_fr_is_french(self):
        for partner in self:
            partner.l10n_fr_is_french = partner.country_code in self.env['res.company']._get_france_country_codes()

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class L10nLatamIdentificationType(models.Model):
    _name = 'l10n_latam.identification.type'
    _inherit = ['l10n_latam.identification.type', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        if self.env.company.country_id.code == 'CL':
            return ['name']
        return result

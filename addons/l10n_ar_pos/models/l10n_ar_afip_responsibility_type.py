# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class L10nArAfipResponsibilityType(models.Model):
    _name = 'l10n_ar.afip.responsibility.type'
    _inherit = ['l10n_ar.afip.responsibility.type', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name']

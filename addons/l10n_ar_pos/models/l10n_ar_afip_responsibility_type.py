# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import l10n_ar, point_of_sale

from odoo import models, api


class L10nArAfipResponsibilityType(models.Model, l10n_ar.L10nArAfipResponsibilityType, point_of_sale.PosLoadMixin):
    _name = 'l10n_ar.afip.responsibility.type'

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name']

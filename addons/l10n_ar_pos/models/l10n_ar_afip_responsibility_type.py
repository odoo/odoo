# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons import l10n_ar, point_of_sale


class L10n_ArAfipResponsibilityType(l10n_ar.L10n_ArAfipResponsibilityType, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name']

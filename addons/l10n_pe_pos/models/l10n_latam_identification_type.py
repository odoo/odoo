# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api
from odoo.addons import point_of_sale, l10n_pe


class L10n_LatamIdentificationType(l10n_pe.L10n_LatamIdentificationType, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_domain(self, data):
        if self.env.company.country_id.code == "PE":
            return [("l10n_pe_vat_code", "!=", False)]
        else:
            return super()._load_pos_data_domain(data)

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name']

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class L10nPhDiscountPrivilege(models.Model):
    _inherit = ["l10n_ph.discount.privilege", "pos.load.mixin"]
    _name = "l10n_ph.discount.privilege"

    @api.model
    def _load_pos_data_domain(self, data):
        return [("company_id", "in", data["pos.config"].company_id.ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ["id", "name", "discount_type", "discount_amount"]

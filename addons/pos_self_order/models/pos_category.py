# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.fields import Domain


class PosCategory(models.Model):
    _inherit = "pos.category"

    self_order_available = fields.Boolean(
        string="Available in Self Order",
        help="If unchecked, this category is not shown in the Self Order menu. "
            "Its products remain selectable as combo choices.",
        default=True,
    )

    @api.model
    def _load_pos_self_data_domain(self, data):
        domain = super()._load_pos_self_data_domain(data)
        config = data['pos.config']
        if config.limit_categories and config.iface_available_categ_ids:
            # In the self order menu a category is only reachable through its parents, so the
            # ancestors of the available categories are loaded as well. They are only used to
            # build the category bar, their own products are not available.
            domain = Domain.OR([
                Domain(domain),
                Domain('id', 'parent_of', config.iface_available_categ_ids.ids),
            ])
        return domain

    @api.model
    def _load_pos_self_data_fields(self, config):
        return [*super()._load_pos_self_data_fields(config), 'self_order_available']

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name in ["image_128", "image_512"]:
            return True
        return super()._can_return_content(field_name, access_token)

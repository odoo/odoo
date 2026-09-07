# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResGroups(models.Model):
    _inherit = 'res.groups'

    def _get_light_group_xmlids(self):
        return super()._get_light_group_xmlids() + (
            'product.group_product_pricelist',
            'product.group_product_variant',
            'product.group_show_uom_price',
        )

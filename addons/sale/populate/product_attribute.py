# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import populate


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    def _populate_factories(self):

        return super()._populate_factories() + [
            ("display_type", populate.randomize(['radio', 'select', 'color'], [6, 3, 1])),
        ]


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"

    def _populate_factories(self):
        attribute_ids = self.env.registry.populated_models["product.attribute"]
        color_attribute_ids = self.env["product.attribute"].search([
            ("id", "in", attribute_ids),
            ("display_type", "=", "color"),
        ]).ids

        def get_custom_values(iterator, field_group, model_name):
            r = populate.Random('%s+fields+%s' % (model_name, field_group))
            for _, values in enumerate(iterator):
                attribute_id = values.get("attribute_id")
                if attribute_id in color_attribute_ids:
                    values["html_color"] = r.choice(
                        ["#FFFFFF", "#000000", "#FFC300", "#1BC56D", "#FFFF00", "#FF0000"],
                    )
                elif not r.getrandbits(4):
                    values["is_custom"] = True
                yield values

        return super()._populate_factories() + [
            ("_custom_values", get_custom_values),
        ]

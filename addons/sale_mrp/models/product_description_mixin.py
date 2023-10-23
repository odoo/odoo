# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ProductDescriptionMixin(models.AbstractModel):
    _inherit = 'product.description.mixin'

    def is_linkable_to_model(self, pcav):
        is_super_linkable = super().is_linkable_to_model(pcav)
        # this additionnal condition happens when linking the pcav from a SO to a MO
        # the pcav[2] will only contain an array of ids of the pcav to link.
        # we do not need to update the res_model because there is already a field related the SOL
        # in the product.attribute.custom.value model
        return is_super_linkable and isinstance(pcav[2], dict)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class IrModel(models.Model):
    _inherit = "ir.model"

    @api.model
    def has_searchable_parent_relation(self, model_name):
        model = self.env.get(model_name)
        if model is None or not model.has_access("read"):
            return False
        # we consider only stored parent relationships were meant to
        # be used to be searched
        return model._parent_store and model._parent_name in model._fields

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

class IrQWeb(models.AbstractModel):
    _inherit = 'ir.qweb'

    def _get_template_cache_keys(self):
        return super()._get_template_cache_keys() + ["studio"]

    def _prepare_environment(self, values):
        # blacklist known parasite variables
        if self._context.get("studio"):
            for k in ["main_object"]:
                if k in values:
                    del values[k]
        return super()._prepare_environment(values)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _


class StockMove(models.Model):
    _inherit = "stock.move"

    def _is_returned(self, valued_type):
        if self.unbuild_id and self.unbuild_id.mo_id:   # unbuilding a MO
            return True
        return super()._is_returned(valued_type)

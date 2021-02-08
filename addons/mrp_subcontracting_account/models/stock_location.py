# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class StockLocation(models.Model):
    _inherit = "stock.location"

    def _should_be_valued(self):
        res = super()._should_be_valued()
        if self.company_id.subcontracting_location_id:
            res &= self != self.company_id.subcontracting_location_id
        return res

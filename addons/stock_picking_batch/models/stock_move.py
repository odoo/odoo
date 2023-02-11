# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.osv import expression


class StockMove(models.Model):
    _inherit = "stock.move"

    def _search_picking_for_assignation_domain(self):
        domain = super()._search_picking_for_assignation_domain()
        domain = expression.AND([domain, ['|', ('batch_id', '=', False), ('batch_id.is_wave', '=', False)]])
        return domain

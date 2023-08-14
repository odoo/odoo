# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _should_bypass_reservation(self, location):
        """ If the move line is subcontracted then ignore the reservation. """
        should_bypass_reservation = super(StockMoveLine, self)._should_bypass_reservation(location)
        if not should_bypass_reservation and self.move_id.is_subcontract:
            return True
        return should_bypass_reservation

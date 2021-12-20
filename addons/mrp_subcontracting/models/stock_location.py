# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockLocation(models.Model):
    _inherit = 'stock.location'

    def _check_access_putaway(self):
        """ Use sudo mode for subcontractor """
        if self.env.user.partner_id.is_subcontractor:
            return self.sudo()
        else:
            return super()._check_access_putaway()

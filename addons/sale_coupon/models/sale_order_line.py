# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class OrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_name(self):
        # Avoid computing the name for reward lines
        reward = self.filtered('is_reward_line')
        super(OrderLine, self - reward)._compute_name()

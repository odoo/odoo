# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.
from odoo import models, _
from odoo.exceptions import ValidationError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    def action_apply_inventory(self):
        res = super(StockQuant, self).action_apply_inventory()
        if not self.env.user.has_group("bi_update_qty_disable.group_onhand_qty_user"):
            raise ValidationError(
                _("You don't have access rights for update on hand quantity!"))
        return res

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import purchase_stock


class AccountMoveLine(purchase_stock.AccountMoveLine):

    def _get_stock_valuation_layers(self, move):
        """ Do not handle the invoice correction for kit. It has to be done
        manually """
        layers = super()._get_stock_valuation_layers(move)
        return layers.filtered(lambda svl: svl.product_id == self.product_id)

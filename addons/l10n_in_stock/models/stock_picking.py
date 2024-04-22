# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockPicking(models.Model):
    _inherit = 'stock.picking'


    def _should_generate_commercial_invoice(self):
        super(StockPicking, self)._should_generate_commercial_invoice()
        return True

    def _get_l10n_in_purchase(self):
        pass

    def _get_l10n_in_sale(self):
        pass

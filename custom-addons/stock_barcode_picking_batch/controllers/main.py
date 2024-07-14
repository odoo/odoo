# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request
from odoo.addons.stock_barcode.controllers.stock_barcode import StockBarcodeController


class StockBarcodePickingBatchController(StockBarcodeController):

    @http.route()
    def main_menu(self, barcode):
        ret_open_batch_picking = self.try_open_batch_picking(barcode)
        if ret_open_batch_picking:
            return ret_open_batch_picking
        return super().main_menu(barcode)

    def try_open_batch_picking(self, barcode):
        batch_picking = request.env['stock.picking.batch'].search([
            ('name', '=', barcode),
        ], limit=1)
        if batch_picking:
            action = batch_picking.action_client_action()
            action['context'] = {'active_id': batch_picking.id}
            action = {'action': action}
            return action
        return False

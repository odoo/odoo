# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class StockBackorderConfirmation(models.TransientModel):
    _name = 'stock.backorder.confirmation'
    _description = 'Backorder Confirmation'

    pick_id = fields.Many2one('stock.picking')

    @api.model
    def default_get(self, fields):
        res = super(StockBackorderConfirmation, self).default_get(fields)
        if 'pick_id' in fields and self._context.get('active_id') and not res.get('pick_id'):
            res = {'pick_id': self._context['active_id']}
        return res

    @api.one
    def _process(self, cancel_backorder=False):
        operations_to_delete = self.pick_id.pack_operation_ids.filtered(lambda o: o.qty_done <= 0)
        for pack in self.pick_id.pack_operation_ids - operations_to_delete:
            pack.product_qty = pack.qty_done
        operations_to_delete.unlink()
        self.pick_id.do_transfer()
        if cancel_backorder:
            backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', self.pick_id.id)])
            backorder_pick.action_cancel()
            self.pick_id.message_post(body=_("Back order <em>%s</em> <b>cancelled</b>.") % (backorder_pick.name))

    @api.multi
    def process(self):
        self._process()

    @api.multi
    def process_cancel_backorder(self):
        self._process(cancel_backorder=True)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api
from openerp.tools.translate import _

class stock_backorder_confirmation(models.TransientModel):
    _name = 'stock.backorder.confirmation'
    _description = 'Backorder Confirmation'

    pick_id = fields.Many2one('stock.picking')

    @api.model
    def default_get(self, fields):
        res = {}
        active_id = self._context.get('active_id')
        if active_id:
            res = {'pick_id': active_id}
        return res

    @api.multi
    def _process(self, cancel_backorder=False):
        self.ensure_one()
        for pack in self.pick_id.pack_operation_ids:
            if pack.qty_done > 0:
                pack.product_qty = pack.qty_done
            else:
                pack.unlink()
        self.pick_id.do_transfer()
        if cancel_backorder:
            backorder_pick = self.env['stock.picking'].search([('backorder_id', '=', self.pick_id.id)])
            backorder_pick.action_cancel()
            self.pick_id.message_post(body=_("Back order <em>%s</em> <b>cancelled</b>.") % (backorder_pick.name))

    @api.multi
    def process(self):
        self.ensure_one()
        self._process()

    @api.multi
    def process_cancel_backorder(self):
        self.ensure_one()
        self._process(cancel_backorder=True)

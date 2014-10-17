# -*- encoding: utf-8 -*-

from openerp import models, api


class lunch_cancel(models.TransientModel):
    """ lunch cancel """
    _name = 'lunch.cancel'
    _description = 'cancel lunch order'

    @api.multi
    def cancel(self):
        order_lines = self.env['lunch.order.line'].browse(self._context.get('active_ids'))
        return order_lines.cancel()

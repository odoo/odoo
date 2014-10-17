# -*- encoding: utf-8 -*-

from openerp import models, api


class lunch_order_order(models.TransientModel):
    """ lunch order meal """
    _name = 'lunch.order.order'
    _description = 'Wizard to order a meal'

    @api.multi
    def order(self):
        order_lines = self.env['lunch.order.line'].browse(self._context.get('active_ids'))
        return order_lines.order()

# -*- encoding: utf-8 -*-

from openerp import models, api


class lunch_validation(models.TransientModel):
    """ lunch validation """
    _name = 'lunch.validation'
    _description = 'lunch validation for order'

    @api.multi
    def confirm(self):
        order_lines = self.env['lunch.order.line'].browse(self._context.get('active_ids'))
        return order_lines.confirm()

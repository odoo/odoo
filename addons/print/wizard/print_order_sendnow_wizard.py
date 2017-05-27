# -*- coding: utf-8 -*-
from openerp import api, fields, models


class PrintOrderSendnowWizard(models.TransientModel):
    """ This wizard aims to directly (and manually) process on the sending method on the
        selected Print Order. Otherwise the orders will be process by the cron.
    """

    _name = 'print.order.sendnow.wizard'
    _rec_name = 'create_date'


    def _default_print_order_ids(self):
        orders = self.env['print.order'].browse(self.env.context.get('active_ids', [])).filtered(lambda order: order.state != 'sent')
        return [(4, order.id) for order in orders]

    # this should be a One2Many, but One2Many computed doesn't work very well.
    print_order_ids = fields.Many2many(comodel_name='print.order', default=_default_print_order_ids)


    @api.multi
    def action_apply(self):
        self.ensure_one()
        self.env['print.order'].process_order_queue(self[0].print_order_ids.ids)
        return {'type': 'ir.actions.act_window_close'}

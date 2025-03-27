import logging

from odoo import models, fields

_logger = logging.getLogger("===+++ Sale Order +++===")


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    instance_id = fields.Many2one(comodel_name='eg.ecom.instance', string='Instance')

    def action_confirm(self):
        """
        In this update order status from odoo to middle layer and woocommerce.
        """
        res = super(SaleOrder, self).action_confirm()
        woo_api = self.instance_id
        if woo_api and woo_api.provider == "eg_wocommerce":  # TODO : Change by akash
            try:  # TODO : Change by akash
                wcapi = woo_api.get_wcapi_connection()
                order_state = self.env['order.state.line'].search([('odoo_order_state', '=', self.state)])
                data = {'status': order_state.woo_order_state, }
                woo_order_id = self.env['eg.sale.order'].search(
                    [('odoo_order_id', '=', self.id), ('instance_id', '=', self.instance_id.id)])
                if woo_order_id:  # TODO : Change by akash
                    woo_order_id.write({'status': order_state.woo_order_state})
                    wcapi.put("orders/{}".format(woo_order_id.inst_order_id), data).json()
            except Exception as e:
                _logger.info("{}".format(e))
        return res

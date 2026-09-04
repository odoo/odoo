from odoo import models, fields


class SaleOrderWizard(models.TransientModel):
    _name = 'sale.order.wizard'

    woo_order_state = fields.Selection(
        [('pending', 'Pending'), ("processing", "Processing"), ("on-hold", "On-Hold"), ("cancelled", "Cancelled"),
         ("refunded", "Refunded"), ("failed", "Failed"), ("trash", "Trash"), ("completed", "Completed")])

    def update_woo_order_state(self):
        """
        In this update order status from wizard to middle layer and woocommerce
        :return: Nothing
        """
        active_order_id = self.env['sale.order'].browse(self._context.get('active_id'))
        woo_order_id = self.env['eg.sale.order'].search(
            [('odoo_order_id', '=', active_order_id.id), ('instance_id', '=', active_order_id.instance_id.id)])
        if woo_order_id:  # New Change
            woo_order_id.write({'status': self.woo_order_state})
            woo_order_id.woo_update_order_state(self.woo_order_state)

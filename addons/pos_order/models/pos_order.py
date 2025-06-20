import logging
from odoo import fields, models, tools
import psycopg2

_logger = logging.getLogger(__name__)


class PosOrder(models.Model):
    _inherit = "pos.order"

    def create_picking_set_shipping(self, order_id):
        order = self.browse(order_id)
        order.ensure_one()

        if order.name == "/":
            order.name = order._compute_order_name()

        if not order.shipping_date:
            order.shipping_date = fields.Date.today()

        if not order.picking_ids:
            order._create_order_picking()
   
    def check_existing_picking(self, order_id):
        order = self.search([('access_token', '=', order_id)], limit=1)
        return {
            'hasPicking': bool(order.picking_ids),
            'trackingNumber': order.tracking_number or 'N/A'
        }
        
    def _process_saved_order(self, draft):
        self.ensure_one()
        if not draft:
            try:
                self.action_pos_order_paid()
            except psycopg2.DatabaseError:
                raise
            except Exception as e:
                _logger.error('Could not fully process the POS Order: %s', tools.exception_to_unicode(e))
            if not self.picking_ids:
                self._create_order_picking()
                
            self.picking_ids.scheduled_date = self.shipping_date
            self._compute_total_cost_in_real_time()

        if self.to_invoice and self.state == 'paid':
            self._generate_pos_order_invoice()

        return self.id

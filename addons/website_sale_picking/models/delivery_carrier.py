from odoo import models, fields, api
from odoo.exceptions import UserError


class DeliveryCarrier(models.Model):
    _inherit = 'delivery.carrier'

    # Onsite delivery means the client comes to a physical store to get the products himself.
    delivery_type = fields.Selection(selection_add=[
        ('onsite', 'On Site')
    ], ondelete={'onsite': lambda record: record.write({'delivery_type': 'fixed'})})

    # If set, the sales order shipping address will take this warehouse's address.
    warehouse_id = fields.Many2one('stock.warehouse', 'Pick from')

    @api.constrains('warehouse_id', 'company_id')
    def _check_warehouse_same_company(self):
        """
            Don't allow the user to set a warehouse from a different company than the delivery carrier
        """
        if self.warehouse_id.company_id != self.company_id:
            raise UserError('The warehouse must belong to the same company')

    def onsite_rate_shipment(self, order):
        """
        Required to show the price on the checkout page for the onsite delivery type
        """
        return {
            'success': True,
            'price': self.product_id.list_price,
            'error_message': False,
            'warning_message': False
        }

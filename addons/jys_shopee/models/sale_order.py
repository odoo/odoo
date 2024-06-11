from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_shopee_order = fields.Boolean('Shopee Order', copy=False, default=False)
    is_shopee_cod = fields.Boolean('Shopee COD', copy=False, default=False)
    is_shopee_return = fields.Boolean('Shopee Returned', default=False)
    
    tracking_no = fields.Char('Tracking Number', copy=False)
    shopee_ordersn = fields.Char('Shopee Serial Number', copy=False)

    shopee_payment_date = fields.Datetime('Shopee Payment Date', copy=False)
    shopee_max_ship_date = fields.Datetime('Shopee Max Shipment Date', copy=False)
    
    shopee_actual_shipping_cost = fields.Float('Shopee Actual Shipping Cost', copy=False)
    shopee_shipping_cost_rebate = fields.Float('Shopee Shipping Cost Rebate', copy=False)
    shopee_commission_fee = fields.Float('Shopee Commission Fee', copy=False)
    
    shopee_shop_id = fields.Many2one('shopee.shop', 'Shopee Shop', copy=False)

    _sql_constraints = [
        ('shopee_ordersn_uniq', 'unique(shopee_ordersn)', 'You cannot have more than one order with the same Shopee Serial Number!')
    ]
    
    # Cronjob Get Order
    def run_scheduler_get_order(self, shop_id=False, is_cron_input_so=False):
        wizard_obj = self.env['shopee.get.order']
        company = self.env.user.company_id

        if shop_id:
            shops = self.env['shopee.shop'].search([('shop_id', '=', shop_id)])
        else:
            shops = company.shopee_shop_ids

        for shop in shops:
            wizard_id = wizard_obj.create({
                'shop_id': shop.id,
                'is_continue': True
            })
            wizard_id.action_confirm(is_cron_input_so)


        return True
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    price_after_tax = fields.Float('Price After Tax', copy=False)

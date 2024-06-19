from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class SaleOrder(models.Model):
    _inherit = "sale.order"

    is_tiktok_order = fields.Boolean('Tiktok Order', copy=False, default=False)
    is_tiktok_cod = fields.Boolean('Tiktok COD', copy=False, default=False)
    is_tiktok_return = fields.Boolean('Tiktok Returned', default=False)
    marketplace_no = fields.Char('Marketplace Number')
    tracking_no = fields.Char('Tracking Number', copy=False)
    tiktok_ordersn = fields.Char('Tiktok Serial Number', copy=False)

    tiktok_payment_date = fields.Datetime('Tiktok Payment Date', copy=False)
    tiktok_max_ship_date = fields.Datetime('Tiktok Max Shipment Date', copy=False)
    slowest_delivery_date = fields.Datetime('Slowest Delivery Date', copy=False)
    
    tiktok_actual_shipping_cost = fields.Float('Tiktok Actual Shipping Cost', copy=False)
    tiktok_shipping_cost_rebate = fields.Float('Tiktok Shipping Cost Rebate', copy=False)
    tiktok_commission_fee = fields.Float('Tiktok Commission Fee', copy=False)
    
    tiktok_shop_id = fields.Many2one('tiktok.shop', 'Tiktok Shop', copy=False)
    buyer_message = fields.Text('Buyer Message')
    marketplace_partner_id = fields.Many2one('res.partner','Marketplace')

    _sql_constraints = [
        ('tiktok_ordersn_uniq', 'unique(tiktok_ordersn)', 'You cannot have more than one order with the same Tiktok Serial Number!')
    ]
    
    # Cronjob Get Order
    def run_scheduler_get_order(self, shop_id=False):
        wizard_obj = self.env['tiktok.get.order']
        company = self.env.user.company_id

        if shop_id:
            shops = self.env['tiktok.shop'].search([('shop_id', '=', shop_id)])
        else:
            shops = company.tiktok_shop_ids

        for shop in shops:
            wizard_id = wizard_obj.create({
                'shop_id': shop.id,
                'is_continue': True
            })
            wizard_id.action_confirm()


        return True
    
class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    
    price_after_tax = fields.Float('Price After Tax', copy=False)

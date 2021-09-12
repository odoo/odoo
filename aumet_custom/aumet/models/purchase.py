from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection([
        ('draft', 'RFQ'),
        ('in marketplace', 'In Marketplace'),
        ('sent', 'RFQ Sent'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled')
    ], string = 'Status', readonly = True, index = True, copy = False, tracking = True)
    @api.depends('state')
    def _calculate_state(self):
        pass
        # self.state = "in marketplace"

    @api.model
    def view_init(self, fields_list):
        pass
    
    def write(self, vals):
        super(PurchaseOrder, self).write(vals)
    
    def action_added_to_cart(self):
        for po in self:
            if po.order_line.mp_added_to_cart:
                po.state = 'in marketplace'

    def button_marketplace(self):
        if self.order_line.is_in_marketplace:
            self.write({'state': 'in marketplace'})
        return {}
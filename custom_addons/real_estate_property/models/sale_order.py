from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    property_id = fields.Many2one('property', string='Property')

    def action_confirm(self):
        res = super(SaleOrder,self).action_confirm()
        print("Printing from custom action confirm method")
        return res


    def action_do_something(self):
        print("Doing something from sale order")
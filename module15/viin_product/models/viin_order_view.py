from odoo import fields, models, api


class ViinOrder(models.AbstractModel):
    _name = 'viin.orderview'
    _description = 'Viin orderview'
    

                
    order_code = fields.Char(string='category Code',readonly = True)
    note = fields.Text(string='category note', translate=True , size=300)
    product_ids = fields.Many2many('viin.product', string='Products')
    # attribute_ids = fields.One2many('viin.productattribute', 'category_id', string='Attributes')
    total_price = fields.Integer(string='Total price', compute='_compute_total_price',
                     store=True, 
                     compute_sudo=True)

    customer_id = fields.Many2one('viin.customer', string='Customer')
    
    @api.depends('product_ids')
    def _compute_total_price(self):
        for r in self:
            if r.product_ids:
                r.total_price = 100
            else:
                r.total_price = 0
    
   
   
    
    


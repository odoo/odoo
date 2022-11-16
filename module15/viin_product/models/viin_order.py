from odoo import fields, models, api


class ViinOrder(models.Model):
    _name = 'viin.order'
    _description = 'Viin order'
    

                
    order_code = fields.Char(string='category Code',readonly = True, compute='_compute_code',store = True)
    note = fields.Text(string='category note', translate=True )
    product_ids = fields.Many2many('viin.product', string='Products',required = True)
    # attribute_ids = fields.One2many('viin.productattribute', 'category_id', string='Attributes')
    total_price = fields.Integer(string='Total price', compute='_compute_total_price',
                     store=True, 
                     compute_sudo=True)

    # customer_id = fields.Many2one('viin.customer', string='Customer',ondelete="restrict")
    customer_id = fields.Many2one('viin.customer', string='Customer', required=True)


    
    @api.depends('product_ids')
    def _compute_total_price(self):
        for r in self:
            if r.product_ids:
                total = 0
                for p in r.product_ids:
                    total += p.price
                r.total_price = total
            else:
                r.total_price = 0
    
    @api.depends('product_ids')
    def _compute_code(self):
        last_id = self.env['viin.order'].search([])[-1].id
        self.order_code = 'OD'+str(last_id+1)

        # for r in self:
        #     if r.product_ids:
        #         total = 0
        #         for p in r.product_ids:
        #             total += p.price
        #         r.total_price = total
        #     else:
        #         r.total_price = 0
    
   
   
    
    


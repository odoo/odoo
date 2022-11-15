from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ViinProduct(models.Model):
    _name = 'viin.product'
    _description = 'Viin product'
    
    
    def _default_date(self):
        return fields.Date.today()
            
    
    
    name = fields.Char(string='Product Name', required=True, translate=True , help="Enter the product name")
    # product_code = fields.Char(string='Product Code', readonly=True)
    product_code = fields.Char(string='Product Code', compute='_compute_code', groups='viin_product.viin_product_group_admin',
                     store=True,
                     compute_sudo=True)
    note = fields.Text(string='Product note', translate=True)
    description = fields.Html(string='Product description' )
    image = fields.Image(string='Product Image')
    total = fields.Integer(string='Total product')
    rating = fields.Float(string='Product rating', default = 5, readonly = True )
    sold_out = fields.Boolean(string='Out of stock')
    attach_file = fields.Many2many('ir.attachment', string='Attach files')
    currency_id = fields.Many2one('res.currency', string='Currency')
    price = fields.Monetary('Amount Paid')
    date_of_manufacture = fields.Date(string='Date of Manufacture',required=True, default = _default_date)
    expiration_date = fields.Date(string='Expiration date',default = _default_date,required=True)
    # category_id = fields.Many2one('category.class', string='Category')
    company_id = fields.Many2one('res.company', string='Company')
    category_ids = fields.Many2many('viin.category', string='Category')
    order_ids = fields.Many2many('viin.order', string='Order')
    supply_ids = fields.Many2many('viin.supply', string='Supply')
    
    dropout_reason = fields.Text(string='Dropout Reason')

    def action_dropout(self):
        return self.env.ref('viin_product.viin_product_dropout_wizard_action').read()[0]



    # attachment_ids = fields.Many2one('res.',string='Attachment')
    
    _sql_constraints = [
        ('product_code_unique', 'unique(product_code)', "The product code must be unique!"),
        ('check_total_product', 'CHECK(total >= 0)', "The Total Product must be greater than 0!")
    ]
    
   
    
    @api.depends('name')
    def _compute_code(self):
        for r in self:
            if r.id:
                r.product_code = 'SP' + str(r.id)
            else:
                r.product_code = 'SP#'
                
    @api.constrains('expiration_date')
    def _check_date(self):
            for r in self:
                if(r.date_of_manufacture and r.expiration_date):
                    if r.date_of_manufacture.strftime('%Y-%m-%d') > r.expiration_date.strftime('%Y-%m-%d'):
                        raise ValidationError('Expiration date must be greater than Date of Manufacture')

    @api.constrains('date_of_manufacture')
    def _check_date_of_manufacture(self):
        for r in self:
            if r.date_of_manufacture > fields.Date.today():
                raise ValidationError(_("Date of Manufacture must be in the past"))
    
    # @api.depends('expiration_date')
    # def _compute_age(self):
    #     curent_year = fields.Date.today().year
    #     for r in self:
    #         if r.date_of_birth:
    #             r.age = curent_year - r.date_of_birth.year
    #         else:
    #             r.age = 0


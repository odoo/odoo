from odoo import fields, models, api
from odoo.exceptions import ValidationError


class ViinCategory(models.Model):
    _inherit = "viin.base.model"
    _name = 'viin.category'
    _description = 'Viin category'
    
    
    def _default_date(self):
        return fields.Date.today()
            
    
    
    name = fields.Char(string='category Name', required=True, translate=True , help="Enter the category name")
    category_code = fields.Char(string='category Code', compute='_compute_code', groups='viin_category.viin_category_group_admin',
                     store=True,
                     compute_sudo=True)
    note = fields.Text(string='category note', translate=True )
    image = fields.Image(string='category Image')
    parent_id = fields.Many2one('viin.category', string='Parent Group', ondelete='restrict')

    attribute_ids = fields.One2many('viin.productattribute', 'category_id', string='Attributes')
    product_ids = fields.Many2many('viin.product', string='Products')
    
    _parent_store = True
    _parent_name = "parent_id" # tùy chọn nếu trường là cấp cha

    parent_path = fields.Char(index=True,readonly = True)

        
    @api.depends('name')
    def _compute_code(self):
        for r in self:
            if r.id:
                r.category_code = 'SP' + str(r.id)
            else:
                r.category_code = 'SP#'
                
    @api.constrains('parent_id')
    def _check_hierarchy(self):
        if not self._check_recursion():
            raise ValidationError('Error! You cannot create recursivecategories.')
   
   
    
    


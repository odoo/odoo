from odoo import fields, models


class ViinProductAttribute(models.Model):
    _name = 'viin.productattribute'
    _description = 'Viin product attributes'
    
    
    def _default_date(self):
        return fields.Date.today()
            
    
    
    name = fields.Char(string='Attribute Name', required=True, translate=True , help="Enter the attribute name")
    value  = fields.Char(string = 'Attribute value', help="Enter the attribute value")
    description = fields.Html(string='category description' )
    category_id = fields.Many2one('viin.category', string='Category')

        

   
   
    
    


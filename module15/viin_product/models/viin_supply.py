from odoo import fields, models, api


class ViinSupply(models.Model):
    _name = 'viin.supply'
    _description = 'Viin supply'
    
    
    def _default_date(self):
        return fields.Date.today()
            
    
    
    name = fields.Char(string='Supply Name', required=True, translate=True , help="Enter the supply name")
    supply_code = fields.Char(string='supply Code', compute='_compute_code', groups='viin_supply.viin_supply_group_admin',
                     store=True,
                     compute_sudo=True)
    address = fields.Text(string='address', translate=True , help="Enter the address")
    note = fields.Text(string='supply note', translate=True )
    image = fields.Image(string='supply Image')
    product_ids = fields.Many2many('viin.product', string='Products')

        
    @api.depends('name')
    def _compute_code(self):
        for r in self:
            if r.id:
                r.supply_code = 'SP' + str(r.id)
            else:
                r.supply_code = 'SP#'
   
   
    
    


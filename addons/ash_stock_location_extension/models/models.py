from odoo import models, fields

class StockLocation(models.Model):
    _inherit = 'stock.location'

    system_type = fields.Selection(
        [('voice', 'Voice'), 
         ('geek', 'Geek'), 
         ('manual', 'Manual')], 
        string='System Type'
    )
    check_digit = fields.Char(string='Check Digit')

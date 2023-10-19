from odoo import models, fields

class LoadShapeDetails(models.Model):
    _name = "loadshape_details"
    _description = "Description of the LoadShapeDetails model"
    name = fields.Char()
    contract_id = fields.Many2one('contract', string='Contract')
    powerdate = fields.Date(string='Power Date')
    powerhour = fields.Integer(string='Power Hour')
    power = fields.Float(string='Power')
    powerprice = fields.Float(string='Power Price')
    powerunit = fields.Char(string='Power Unit')
    powerfinalprice = fields.Float(string='Power Final Price')
    powerfinal = fields.Float(string='Power Final')


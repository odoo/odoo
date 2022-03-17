
from odoo import api, fields, models

class RealEstateAgent(models.Model):
    _name = "realestate.agent"
    _description = "Real Estate Agent"

    name = fields.Many2one(comodel_name='res.partner')
    age = fields.Integer(string="Age")
    gender = fields.Selection([('male', 'Male'), ('female', 'Female'), ('gay', 'Gay')], string="Gender")
    count = fields.Selection([('china', 'China'), ('usa', 'United State'), ('thailand', 'Thailand')], string="Country")


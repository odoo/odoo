from odoo import models, fields

class Period(models.Model):
    _name = "period"
    _description = "Description of the Period model"
    name = fields.Char()
    type = fields.Selection([('day', 'Day'), ('wd', 'Weed'), ('year', 'Year')], 'Type')
    start_day = fields.Integer(string='Start Day')
    start_month= fields.Integer(string='Start Month')
    start_hour = fields.Integer(string='Start Hour')
    end_day = fields.Integer(string='End Day')
    end_month= fields.Integer(string='End Month')
    end_hour = fields.Integer(string='End Hour')
    contract_ids = fields.One2many('contract',"period_id", string='Contracts')

    

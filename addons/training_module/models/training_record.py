from odoo import fields, models


class TrainingRecord(models.Model):
    _name = 'training.record'
    _description = 'Training Record'

    name = fields.Char(string='Name', required=True)
    quantity = fields.Integer(string='Quantity', default=1)
    training_date = fields.Date(string='Training Date')
    is_completed = fields.Boolean(string='Completed', default=False)
    partner_id = fields.Many2one('res.partner', string='Partner')

from odoo import fields, models, api


class ResDeleteHistory(models.Model):
    _name = 'res.delete.history'
    _description = 'Delete History'
    _order = 'date desc'

    name = fields.Char()
    model = fields.Char(
        string='Related Document Model')
    note = fields.Text(
        string="Details")
    date = fields.Datetime(
        string='Delete Date')
    res_id = fields.Integer(
        string='Related Document ID')
    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Deleted By')
    

from odoo import fields, models, api, _


class StockLocation(models.Model):
    _inherit = 'stock.location'

    user_ids = fields.Many2many(comodel_name='res.users', string='Users')

from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    warehouse_ids = fields.Many2many(comodel_name='stock.warehouse', string='Warehouse')

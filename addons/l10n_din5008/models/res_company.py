from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    has_position_column = fields.Boolean(string="Show Position Column in Reports")

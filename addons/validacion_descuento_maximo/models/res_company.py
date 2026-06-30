from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    discount_limit_percentage = fields.Float(
        string='Límite de descuento (%)',
        default=15.0
    )
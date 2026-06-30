from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    discount_limit_percentage = fields.Float(
        string='Límite de descuento (%)',
        related='company_id.discount_limit_percentage',
        readonly=False
    )
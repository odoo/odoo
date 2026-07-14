from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'
    discount_limit_percentage = fields.Float(
        string='Límite de descuento global (%)',
        default=15.0
    )
    limite_descuento_global = fields.Float(
        string='Límite de descuento antiguo (%)',
        related='discount_limit_percentage',
        readonly=False
    )

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'
    discount_limit_percentage = fields.Float(
        string='Límite de descuento (%)',
        related='company_id.discount_limit_percentage',
        readonly=False
    )
    limite_descuento_global = fields.Float(
        string='Límite de descuento antiguo Ajustes (%)',
        related='company_id.discount_limit_percentage',
        readonly=False
    )
from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_language = fields.Selection([
        ('ar_001', 'Arabic'),
        ('en_US', 'English')
    ], default='ar_001', string="Default Language")

    default_currency_id = fields.Many2one(
        'res.currency', 
        string="Default Currency",
        default=lambda self: self.env.ref('base.SAR', raise_if_not_found=False)
    )

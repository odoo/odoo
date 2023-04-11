from odoo import models, fields

class ResCountry(models.Model):
    _inherit = 'res.country'

    l10n_module_id = fields.Many2one('ir.module.module')

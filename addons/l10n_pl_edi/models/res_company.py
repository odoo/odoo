from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'
    l10n_pl_ksef_environment = fields.Selection([('test', 'Test'), ('prod', 'Production')], string="KSeF Environment", default='test')
    l10n_pl_ksef_token = fields.Char(string="KSeF Authorization Token")

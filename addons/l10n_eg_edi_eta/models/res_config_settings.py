from odoo import models, fields

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_eg_client_identifier = fields.Char(related='company_id.l10n_eg_client_identifier', related_inverse=True)
    l10n_eg_client_secret = fields.Char(related='company_id.l10n_eg_client_secret', related_inverse=True)
    l10n_eg_production_env = fields.Boolean(related='company_id.l10n_eg_production_env', related_inverse=True)
    l10n_eg_invoicing_threshold = fields.Float(related='company_id.l10n_eg_invoicing_threshold', related_inverse=True)

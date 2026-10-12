from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_eg_client_identifier = fields.Char(related='company_id.l10n_eg_client_identifier', readonly=False)
    l10n_eg_client_secret = fields.Char(related='company_id.l10n_eg_client_secret', readonly=False)
    l10n_eg_edi_api_mode = fields.Selection(related='company_id.l10n_eg_edi_api_mode', readonly=False)

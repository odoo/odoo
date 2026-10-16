from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_tr_edi_provider = fields.Selection(related='company_id.l10n_tr_edi_provider', readonly=False)

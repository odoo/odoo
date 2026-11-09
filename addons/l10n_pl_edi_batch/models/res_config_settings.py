from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pl_edi_batch_historic_date = fields.Date(related='company_id.l10n_pl_edi_batch_historic_date', readonly=False)

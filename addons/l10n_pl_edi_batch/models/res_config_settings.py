from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_pl_edi_batch_enabled = fields.Boolean(
        string="KSeF batch download",
        config_parameter='l10n_pl_edi_batch.enabled',
    )

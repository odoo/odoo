from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_tr_nilvera_export_alias = fields.Char(
        related='company_id.l10n_tr_nilvera_export_alias',
        string="Nilvera Export Alias",
        readonly=False,
    )

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    l10n_jo_edi_demo_mode = fields.Boolean(string="JoFotara Demo Mode", related='company_id.l10n_jo_edi_demo_mode', readonly=False)

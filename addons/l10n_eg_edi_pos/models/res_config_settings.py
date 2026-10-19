from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pos_l10n_eg_edi_pos_enable = fields.Boolean(related='pos_config_id.l10n_eg_edi_pos_enable', readonly=False)
    pos_l10n_eg_edi_pos_client_id = fields.Char(related='pos_config_id.l10n_eg_edi_pos_client_id', readonly=False)
    pos_l10n_eg_edi_pos_client_secret = fields.Char(related='pos_config_id.l10n_eg_edi_pos_client_secret', readonly=False)
    pos_l10n_eg_edi_pos_serial_number = fields.Char(related='pos_config_id.l10n_eg_edi_pos_serial_number', readonly=False)
    pos_l10n_eg_edi_pos_preprod = fields.Boolean(related='pos_config_id.l10n_eg_edi_pos_preprod', readonly=False)

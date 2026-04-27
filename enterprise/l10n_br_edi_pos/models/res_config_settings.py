# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_l10n_br_is_nfce = fields.Boolean(related="pos_config_id.l10n_br_is_nfce", readonly=False)
    pos_l10n_br_invoice_serial = fields.Char(related="pos_config_id.l10n_br_invoice_serial", readonly=False)

    l10n_br_nfce_next_number = fields.Integer(related="pos_config_id.sequence_id.number_next_actual", readonly=False)
    l10n_br_edi_csc_identifier = fields.Char(related="company_id.l10n_br_edi_csc_identifier", readonly=False)
    l10n_br_edi_csc_number = fields.Char(related="company_id.l10n_br_edi_csc_number", readonly=False)
    l10n_br_edi_url_key_override = fields.Char(related="company_id.l10n_br_edi_url_key_override", readonly=False)
    l10n_br_edi_qr_url_override = fields.Char(related="company_id.l10n_br_edi_qr_url_override", readonly=False)

    def set_values(self):
        """Override. Disable the QR code on the receipt. The receipt will contain the official QR code provided
        by Avalara."""
        super(ResConfigSettings, self).set_values()
        if self.pos_l10n_br_is_nfce:
            self.point_of_sale_use_ticket_qr_code = False

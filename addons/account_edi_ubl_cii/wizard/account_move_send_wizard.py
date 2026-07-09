from odoo import _, api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    @api.depends('invoice_edi_format', 'mail_attachments_widget')
    def _compute_attachments_not_supported(self):
        for wizard in self:
            if not self.env['res.partner']._get_ubl_cii_formats_info().get(wizard.invoice_edi_format):
                wizard.attachments_not_supported = {}
                continue

            _attachments_to_embed, attachments_not_supported = wizard._get_ubl_available_attachments(
                wizard.mail_attachments_widget,
                wizard.invoice_edi_format
            )
            wizard.attachments_not_supported = {
                attachment.id: _("Unsupported file type via %s", wizard.invoice_edi_format)
                for attachment in attachments_not_supported
            }

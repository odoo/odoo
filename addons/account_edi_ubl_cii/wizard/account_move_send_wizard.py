from odoo import _, api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    @api.depends('invoice_edi_format', 'mail_attachments_widget')
    def _compute_attachments_not_supported(self):
        for wizard in self:
            _attachments_to_embed, attachments_not_supported = wizard._get_ubl_available_attachments(
                wizard.mail_attachments_widget,
                wizard.invoice_edi_format
            )
            wizard.attachments_not_supported = {
                attachment.id: _("Unspported file type via %s", wizard.invoice_edi_format)
                for attachment in attachments_not_supported
            }

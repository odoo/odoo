from odoo import api, models


class AccountMoveSendWizard(models.TransientModel):
    _inherit = 'account.move.send.wizard'

    @api.model
    def _action_download(self, attachments):
        attachments = attachments.filtered(lambda att: att.res_model != 'l10n_uy_edi.document')
        return super()._action_download(attachments)

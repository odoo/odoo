from odoo import _, models
from odoo.exceptions import UserError


class AccountResequenceWizard(models.TransientModel):
    _inherit = 'account.resequence.wizard'

    def _frozen_edi_documents(self):
        """Get EDI documents that can't change.

        Their moves are restricted and cannot be resequenced.
        """
        return self.move_ids.edi_document_ids.filtered(
            lambda d: d.edi_format_id._needs_web_services() and d.state == "sent"
        )

    def resequence(self):
        edi_sent_moves = self._frozen_edi_documents()
        if edi_sent_moves:
            raise UserError(_("The following documents have already been sent and cannot be resequenced: %s")
                % ", ".join(set(edi_sent_moves.move_id.mapped('name')))
            )
        return super().resequence()

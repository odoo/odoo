from odoo import _, models
from odoo.exceptions import UserError
from odoo.addons import account


class AccountResequenceWizard(account.AccountResequenceWizard):

    def resequence(self):
        edi_sent_moves = self.move_ids.edi_document_ids.filtered(lambda d: d.edi_format_id._needs_web_services() and d.state == 'sent')
        if edi_sent_moves:
            raise UserError(_("The following documents have already been sent and cannot be resequenced: %s")
                % ", ".join(set(edi_sent_moves.move_id.mapped('name')))
            )
        return super().resequence()

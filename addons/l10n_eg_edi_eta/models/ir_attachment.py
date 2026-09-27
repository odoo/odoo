from odoo import api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _prevent_eta_accepted_json_deletion(self):
        description = 'ETA Request-Response JSON not to be deleted'
        attachments_to_check = self.filtered(lambda a: a.description == description and a.res_model == 'account.move')
        related_moves = self.env['account.move'].browse(attachments_to_check.mapped('res_id'))
        if any(
            move
            for move in related_moves
            if move.country_code == 'EG' and move.l10n_eg_edi_submission_state == 'accepted'
        ):
            raise UserError(self.env._("You cannot delete the JSON attachment once invoice is sent to ETA."))

    @api.ondelete(at_uninstall=False)
    def _prevent_eta_accepted_invoice_pdf_deletion(self):
        attachments_to_check = self.filtered(lambda a: a.res_field == 'invoice_pdf_report_file' and a.res_model == 'account.move')
        related_moves = self.env['account.move'].browse(attachments_to_check.mapped('res_id'))
        if any(
            move
            for move in related_moves
            if move.country_code == 'EG' and move.l10n_eg_edi_submission_state == 'accepted'
        ):
            raise UserError(self.env._("You cannot delete PDF of invoice which is already sent to ETA."))

from odoo import _, api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = "ir.attachment"

    @api.ondelete(at_uninstall=False)
    def _unlink_except_posted_pdf_invoices(self):
        '''
        Prevents unlinking of invoice pdfs linked to an invoice that is posted.
        '''
        restricted_moves = self._get_posted_pdf_moves_to_check().filtered(lambda move: move.country_code == 'SA' and move.state == 'posted')
        if restricted_moves:
            raise UserError(_("The Invoice PDF(s) cannot be deleted according to ZATCA rules: %s", ', '.join(restricted_moves.mapped('invoice_pdf_report_id.name'))))

    def _get_posted_pdf_moves_to_check(self):
        '''
        Returns the moves to check whether they can be unlinked.
        '''
        res_ids = [
            att.res_id
            for att in self
            if att.res_model == 'account.move' and att.res_field == 'invoice_pdf_report_file'
        ]
        # the corresponding moves may have been deleted already
        return self.env['account.move'].browse(res_ids).exists()

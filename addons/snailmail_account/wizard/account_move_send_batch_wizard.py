import base64

from odoo import _, fields, models


class AccountMoveSendBatchWizard(models.TransientModel):
    _inherit = 'account.move.send.batch.wizard'

    send_by_post_stamps = fields.Integer(compute='_compute_send_by_post_stamps')

    def _compute_send_by_post_stamps(self):
        letter_model = self.env['snailmail.letter']
        for wizard in self:
            stamps = 0
            # One letter is created per move, not per partner.
            for move in wizard.move_ids:
                if not letter_model._is_valid_address(move.partner_id):
                    continue
                # The letter is billed on the number of pages of the document it carries.
                # The invoice report is not rendered yet at that point, so fall back on a
                # single page for it, but the cover page is already known to be added.
                pages = 1
                if move.invoice_pdf_report_id:
                    pages = letter_model._count_pages_pdf(base64.b64decode(move.invoice_pdf_report_id.datas)) or pages
                if move.company_id.snailmail_cover:
                    # _append_cover_page prepends the cover, plus a blank backside in duplex
                    pages += 2 if move.company_id.snailmail_duplex else 1
                stamps += pages
            wizard.send_by_post_stamps = stamps

    def _compute_summary_data(self):
        # EXTENDS 'account'
        super()._compute_summary_data()
        for wizard in self:
            if wizard.summary_data and 'snailmail' in wizard.summary_data:
                wizard.summary_data['snailmail'].update({'extra': _('(Stamps: %s)', wizard.send_by_post_stamps)})

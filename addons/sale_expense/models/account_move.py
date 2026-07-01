# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _reverse_moves(self, default_values_list=None, cancel=False):
        # EXTENDS sale
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super()._reverse_moves(default_values_list, cancel)

    def button_draft(self):
        # EXTENDS sale
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super().button_draft()

    def unlink(self):
        # EXTENDS sale
        self.expense_ids._sale_expense_reset_sol_quantities()
        return super().unlink()

    def _copy_reinvoiced_expense_receipts(self):
        Attachment = self.env['ir.attachment'].sudo()

        for move in self:
            if move.move_type != 'out_invoice':
                continue

            expenses = move.invoice_line_ids.sale_line_ids.expense_ids.sudo().filtered(
                lambda expense: expense.attach_receipts_to_invoice
            )
            attachments = expenses.attachment_ids
            if not attachments:
                continue

            existing_checksums = set(move.attachment_ids.mapped('checksum'))
            attachment_vals_list = []

            for attachment in attachments:
                # to prevent duplicating the reciept if it's already been attached to the move
                if attachment.checksum and attachment.checksum in existing_checksums:
                    continue

                attachment_vals = attachment.copy_data({
                    'res_model': 'account.move',
                    'res_id': move.id,
                    'raw': attachment.raw,
                })[0]
                attachment_vals_list.append(attachment_vals)

                if attachment.checksum:
                    existing_checksums.add(attachment.checksum)

            if attachment_vals_list:
                created_attachments = Attachment.create(attachment_vals_list)
                attachment_count = len(created_attachments)
                move.message_post(
                    body=self.env._(
                        "1 expense receipt attached from reinvoiced expenses."
                    ) if attachment_count == 1 else self.env._(
                        "%(count)s expense receipts attached from reinvoiced expenses.",
                        count=attachment_count,
                    ),
                    attachment_ids=created_attachments.ids,
                    subtype_xmlid='mail.mt_note',
                )

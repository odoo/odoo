from odoo import models, api


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        if self.env.context.get('sync_attachment', True):
            expenses_attachments = attachments.filtered(lambda att: att.res_model == 'hr.expense')
            if expenses_attachments:
                expenses = self.env['hr.expense'].browse(expenses_attachments.mapped('res_id'))
                for expense in expenses.filtered('sheet_id'):
                    checksums = set(expense.sheet_id.attachment_ids.mapped('checksum'))
                    for attachment in expense.attachment_ids.filtered(lambda att: att.checksum not in checksums):
                        attachment.copy({
                            'res_model': 'hr.expense.sheet',
                            'res_id': expense.sheet_id.id,
                        })
        return attachments

    def unlink(self):
        if self.env.context.get('sync_attachment', True):
            attachments_to_unlink = self.env['ir.attachment']
            expenses_attachments = self.filtered(lambda att: att.res_model == 'hr.expense')
            if expenses_attachments:
                expenses = self.env['hr.expense'].browse(expenses_attachments.mapped('res_id'))
                for expense in expenses.exists().filtered('sheet_id'):
                    checksums = set(expense.attachment_ids.mapped('checksum'))
                    attachments_to_unlink += expense.sheet_id.attachment_ids.filtered(lambda att: att.checksum in checksums)
            sheets_attachments = self.filtered(lambda att: att.res_model == 'hr.expense.sheet')
            if sheets_attachments:
                sheets = self.env['hr.expense.sheet'].browse(sheets_attachments.mapped('res_id'))
                for sheet in sheets.exists():
                    checksums = set((sheet.attachment_ids & sheets_attachments).mapped('checksum'))
                    attachments_to_unlink += sheet.expense_line_ids.attachment_ids.filtered(lambda att: att.checksum in checksums)
            super(IrAttachment, attachments_to_unlink).unlink()
        return super().unlink()

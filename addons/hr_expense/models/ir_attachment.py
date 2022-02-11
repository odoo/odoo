# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models

class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model_create_multi
    def create(self, vals_list):
        """
        In case a new attachment is attached to the hr.expense record that
        is already reported, thus there exists 'hr.expense.sheet' linked to it -
        then the same attachment should be coplied to the corresponding sheet record.
        """
        new_attachments = super().create(vals_list)
        if 'original_id' in self.env['ir.attachment']:
            new_expense_attachments = new_attachments.filtered(lambda a: a.res_model == 'hr.expense')
            for attachment in new_expense_attachments:
                expense_id = self.env['hr.expense'].browse(attachment.res_id)
                if expense_id.sheet_id:
                    attachment.copy({'res_model': 'hr.expense.sheet', 'res_id': expense_id.sheet_id.id, 'original_id': attachment.id})
        return new_attachments

    def unlink(self):
        """
        In case an 'hr.expense' attachment is deleted, and an expense has a 'hr.expense.sheet'
        linked to it, then the attachment - that was originally copied from the expense -
        should be deleted for the sheet record as well.
        """
        if 'original_id' in self.env['ir.attachment']:
            expense_attachments = self.filtered(lambda a: a.res_model == 'hr.expense' and a.res_id)
            if expense_attachments:
                self.env['ir.attachment'].search([
                    ('res_model', '=', 'hr.expense.sheet'),
                    ('original_id', 'in', expense_attachments.ids),
                ]).unlink()

        return super().unlink()

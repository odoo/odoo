# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    def document_hr_expense_create_hr_expense(self):
        if self.filtered(
                lambda doc: doc.type != 'binary' or doc.shortcut_document_id or doc.res_model == 'hr.expense' or (
                        doc.mimetype and 'image' not in doc.mimetype.lower() and 'pdf' not in doc.mimetype.lower())):
            raise UserError(_("This action can only be applied on image and pdf not yet linked to an expense."))

        if not self.env.user.employee_ids:
            raise UserError(_("You must be linked to an employee to create an expense."))
        category_id = self.env.ref("hr_expense.product_product_no_cost").id
        expenses = self.env["hr.expense"].create([{
            'name': document.attachment_id.name,
            'product_id': category_id,
        } for document in self])
        for document, expense in zip(self, expenses):
            if (document.res_model or document.res_id) and document.res_model != 'documents.document':
                # Create new attachment
                attachment = document.attachment_id.with_context(no_document=True).copy({
                    "res_model": expense._name,
                    "res_id": expense.id,
                })
                expense._message_set_main_attachment_id(attachment, force=True)
                document = document.copy({"attachment_id": attachment.id})
            else:
                document.attachment_id.with_context(no_document=True).write({
                    'res_model': expense._name,
                    'res_id': expense.id
                })
                expense._message_set_main_attachment_id(document.attachment_id, force=True)
            document.message_post(body=_('Expense %s created from document', expense._get_html_link()))

        action = self.env["ir.actions.actions"]._for_xml_id("hr_expense.hr_expense_actions_my_all")
        action['domain'] = [('id', 'in', expenses.ids)]
        if len(expenses) == 1:
            action.update({
                "view_mode": 'form',
                "views": [[False, 'form']],
                "res_id": expenses[0].id
            })
        return action

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class WorkflowActionRuleExpense(models.Model):
    _inherit = ['documents.workflow.rule']

    create_model = fields.Selection(selection_add=[('hr.expense', "Expense")])

    def create_record(self, documents=None):
        rv = super().create_record(documents=documents)
        if self.create_model == 'hr.expense':
            category_id = self.env.ref("hr_expense.product_product_no_cost").id
            expenses = self.env["hr.expense"].create([{
                'name': document.attachment_id.name,
                'product_id': category_id,
            } for document in documents])
            for document, expense in zip(documents, expenses):
                if (document.res_model or document.res_id) and document.res_model != 'documents.document':
                    # Create new attachment
                    attachment = document.attachment_id.with_context(no_document=True).copy({
                        "res_model": self.create_model,
                        "res_id": expense.id,
                    })
                    attachment.register_as_main_attachment()
                    document = document.copy({"attachment_id": attachment.id})
                else:
                    document.attachment_id.with_context(no_document=True).write({
                        'res_model': self.create_model,
                        'res_id': expense.id
                    })
                    document.attachment_id.register_as_main_attachment()
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
        return rv

from odoo import fields, models


class HrExpensePostWizard(models.TransientModel):
    _inherit = 'hr.expense.post.wizard'

    attach_receipts_to_invoice = fields.Boolean(
        string="Attach receipts to future related invoices",
    )
    show_attach_receipts_to_invoice = fields.Boolean()

    def action_post_entry(self):
        action = super().action_post_entry()
        expenses = self.env['hr.expense'].browse(self.env.context.get('active_ids', []))
        for expense in expenses:
            expense.attach_receipts_to_invoice = bool(
                self.attach_receipts_to_invoice and expense.sale_order_id
            )
        return action

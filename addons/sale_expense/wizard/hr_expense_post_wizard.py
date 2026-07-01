# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrExpensePostWizard(models.TransientModel):
    _inherit = 'hr.expense.post.wizard'

    attach_receipts_to_invoice = fields.Boolean(
        string="Attach receipts to future related invoices",
    )
    show_attach_receipts_to_invoice = fields.Boolean(
        compute='_compute_show_attach_receipts_to_invoice',
    )

    def _get_active_expenses(self):
        return self.env['hr.expense'].browse(self.env.context.get('active_ids', []))

    @api.depends_context('active_ids')
    def _compute_show_attach_receipts_to_invoice(self):
        expenses = self._get_active_expenses()
        show = any(expense.sale_order_id for expense in expenses)
        for wizard in self:
            wizard.show_attach_receipts_to_invoice = show

    def action_post_entry(self):
        action = super().action_post_entry()
        expenses = self._get_active_expenses()
        expenses.filtered('sale_order_id').write({
            'attach_receipts_to_invoice': self.attach_receipts_to_invoice,
        })
        expenses.filtered(lambda expense: not expense.sale_order_id).write({
            'attach_receipts_to_invoice': False,
        })
        return action

from odoo import api, fields, models
from odoo.exceptions import UserError


class ExpenseAttachmentSelectionWizard(models.TransientModel):
    _name = 'expense.attachment.selection.wizard'
    _description = "Attachment Selection"

    sale_order_id = fields.Many2one('sale.order')
    selected_attachments = fields.Json(
        compute='_compute_selected_attachments',
        readonly=False,
        store=True,
    )

    @api.depends('sale_order_id.expense_ids.attachment_ids')
    def _compute_selected_attachments(self):
        order_attachments_map = self.sale_order_id._get_expense_attachments_not_linked_yet()
        for wizard in self:
            wizard.selected_attachments = [{
                'id': attachment.id,
                'name': attachment.name,
                'selected': True,
            } for attachment in order_attachments_map.get(wizard.sale_order_id, [])]

    def action_import_attachments(self):
        self.ensure_one()
        # check if user has access to selected attachments, and if all attachments are effectively linked to expenses
        selected_attachments = self.env['ir.attachment'].browse([
            attachment['id']
            for attachment in self.selected_attachments
            if attachment['selected']
        ])
        attachments = self.sale_order_id.expense_ids.attachment_ids & selected_attachments
        if not attachments:
            raise UserError(self.env._("Please select at least one attachment to import."))

        copied_attachments_sudo = self.env['ir.attachment'].sudo().create(
            attachments.copy_data({
                'res_model': self.sale_order_id._name,
                'res_id': self.sale_order_id.id,
            })
        )
        self.sale_order_id.message_post(
            body=self.env._("The following expense receipts were attached from reinvoiced expenses."),
            attachment_ids=copied_attachments_sudo.ids,
            subtype_xmlid='mail.mt_note',
        )

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
        order_attachments_map_sudo = self.sale_order_id.sudo()._get_expense_attachments_not_linked_yet()
        for wizard in self:
            wizard.selected_attachments = [{
                'id': attachment_id,
                'name': attachment_name,
                'selected': True,
            } for attachment_id, attachment_name in order_attachments_map_sudo.get(wizard.sale_order_id.id, [])]

    def action_import_attachments(self):
        self.ensure_one()
        self.check_access('write')
        # check if user has access to selected attachments, and if all attachments are effectively linked to expenses
        selected_attachments_sudo = self.env['ir.attachment'].sudo().browse([
            attachment['id']
            for attachment in self.selected_attachments
            if attachment['selected']
        ])
        attachments_sudo = self.sale_order_id.sudo().expense_ids.attachment_ids & selected_attachments_sudo
        if not attachments_sudo:
            raise UserError(self.env._("Please select at least one attachment to import."))

        copied_attachments = self.env['ir.attachment'].create(
            attachments_sudo.copy_data({
                'res_model': self.sale_order_id._name,
                'res_id': self.sale_order_id.id,
            })
        )
        self.sale_order_id.message_post(
            body=self.env._("The following expense receipts were attached from reinvoiced expenses."),
            attachment_ids=copied_attachments.ids,
            subtype_xmlid='mail.mt_note',
        )

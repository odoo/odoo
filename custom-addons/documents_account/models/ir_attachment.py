from odoo import models, api

class IrAttachment(models.Model):
    _inherit = ['ir.attachment']

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for vals, attachment in zip(vals_list, attachments):
            if vals.get('res_model', False) != 'account.move':
                continue
            move = self.env['account.move'].browse(vals.get('res_id', False))
            if move.move_type == 'entry' or (len(move.attachment_ids) == 1 and move.attachment_ids[0] == attachment):
                move._update_or_create_document(attachment.id)
        return attachments

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api

class IrAttachment(models.Model):
    _inherit = ['ir.attachment']

    @api.model_create_multi
    def create(self, vals_list):
        attachments = super().create(vals_list)
        for vals, attachment in zip(vals_list, attachments):
            if vals.get('res_model') != 'account.move':
                continue
            move = self.env['account.move'].browse(vals.get('res_id', False))
            # In order to avoid creation of extra documents we retrict creation of a document to:
            # - attachments of a misc operation
            # - xml file after it has been succesfully registered as move attachment
            # Only in the case where the 'no_document' flag is set to False
            if (
                not self._context.get('no_document')
                and (
                    move.move_type == 'entry'
                    or attachment.mimetype == 'application/xml'
                )
            ):
                move._update_or_create_document(attachment.id)
        return attachments

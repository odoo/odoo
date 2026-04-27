# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    def _unwrap_edi_attachments(self, *args, **kwargs):
        file_data_list = super()._unwrap_edi_attachments(*args, **kwargs)
        for file_data in file_data_list:
            attachment = file_data['attachment']
            if file_data['type'] == 'binary' and attachment.res_model == "account.move":
                move = self.env['account.move'].browse(attachment.res_id)
                if move and move.l10n_in_irn_number:
                    file_data['process_if_existing_lines'] = True
        return file_data_list

    @api.ondelete(at_uninstall=False)
    def _unlink_except_government_document(self):
        """
        Prevents the deletion of attachments related to government-issued documents.
        """
        for attachment in self.filtered(lambda a: a.res_model == 'account.move' and a.mimetype == 'application/json'):
            irn_number = attachment.name.split('.')[0]
            moves = self.env['account.move'].search([('l10n_in_irn_number', 'like', irn_number)])
            if moves:
                raise UserError(_("You can't unlink an attachment that you received from the government"))

        return super()._unlink_except_government_document()

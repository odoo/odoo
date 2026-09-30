from odoo import api, models, _
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_ewaybill_government_document(self):
        """
        Prevents the deletion of attachments related to government-issued documents.
        """
        if any(
            attachment.res_model == 'l10n.in.ewaybill'
            and attachment.mimetype == 'application/json'
            and attachment.res_field == 'attachment_file'
            for attachment in self
        ):
            raise UserError(_("You can't unlink an attachment that you received from the government"))

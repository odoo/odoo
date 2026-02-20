from odoo import api, models
from odoo.exceptions import UserError


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.ondelete(at_uninstall=False)
    def _unlink_except_l10n_es_edi_sii_document(self):
        """
        Prevents the deletion of attachments related to SII-issued documents.
        """
        if any(
            attachment.res_model == 'account.move'
            and attachment.mimetype == 'application/json'
            and attachment.res_field == 'l10n_es_edi_sii_json_file'
            for attachment in self
        ):
            raise UserError(self.env._(
                "You can't unlink an attachment that you sent to SII"
            ))

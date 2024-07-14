from odoo import models


class AccountEdiDocument(models.Model):
    _inherit = "account.edi.document"

    def _filter_edi_attachments_for_mailing(self):
        self.ensure_one()
        if not self.sudo().attachment_id or self.edi_format_id.code != 'pe_ubl_2_1':
            return super()._filter_edi_attachments_for_mailing()
        return {
            'attachments': self.edi_format_id._l10n_pe_edi_unzip_all_edi_documents(self.sudo().attachment_id.datas)
        }

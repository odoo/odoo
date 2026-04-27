from odoo import _, models
from odoo.fields import Command


class AccountEdiProxyClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_import_invoice(self, attachment, partner_endpoint, peppol_state, uuid):
        # EXTENDS account_peppol
        """Save new documents in the Documents app, when a folder has been set on the company.

        Reminder: partner_endpoint DEPRECATED - to be removed in master
        """
        self.ensure_one()
        res = super()._peppol_import_invoice(attachment, partner_endpoint, peppol_state, uuid)

        if self.company_id.documents_account_peppol_folder_id:
            document = self.env['documents.document'].create({
                'attachment_id': attachment.id,
                'folder_id': self.company_id.documents_account_peppol_folder_id.id,
                'tag_ids': [Command.set(self.company_id.documents_account_peppol_tag_ids.ids)],
            })
            document._message_log(
                body=_(
                    "Peppol document (UUID: %(uuid)s) has been received successfully.",
                    uuid=uuid,
                ),
            )
            return res or True

        return res

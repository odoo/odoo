from odoo import models


class Account_Edi_Proxy_ClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_import_document(self, attachment, peppol_state, uuid, journal=None):
        """ Import PEPPOL document as either account.move or sale.order, depending on xml_tree's
        cbc:ProfileID element

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :param journal: journal to use for the new move (otherwise the company's peppol journal will be used)
        :return: the created move (if any)
        """
        self.ensure_one()

        file_data = self.env['sale.order']._to_files_data(attachment)[0]

        if file_data['xml_tree'].findtext('.//{*}ProfileID') == 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3':
            return self._peppol_import_advanced_order(attachment, peppol_state, uuid)

        return super()._peppol_import_document(self, attachment, peppol_state, uuid, journal)

    def _peppol_import_order(self, attachment, peppol_state, uuid):
        """Save new documents in an accounting journal, when one is specified on the company.

        Note: ensure_one() from account_peppol

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :return: UUID to ack, wrapped in dict (e.g. {'uuid': '...'})
        """
        order = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(attachment)
        order.write({
            'peppol_message_uuid': uuid,
            'peppol_order_state': peppol_state,
        })

        return {'uuid': uuid}

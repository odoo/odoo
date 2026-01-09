from base64 import b64encode

from odoo import models

from odoo.addons.purchase_peppol.models.purchase_order import Event


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

        # TODO: centralize modules and handle order, change, and cancel / order response advanced
        # accordingly.
        if file_data['xml_tree'].findtext('.//{*}CustomizationID') == 'urn:fdc:peppol.eu:poacc:trns:order_response:3' \
        and file_data['xml_tree'].findtext('.//{*}ProfileID') == 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3':
            return self._peppol_import_order_response_advanced(attachment, peppol_state, uuid)

        return super()._peppol_import_document(attachment, peppol_state, uuid, journal)

    def _peppol_import_order_response_advanced(self, attachment, peppol_state, uuid):
        """
        Import order response advanced document.

        Note: ensure_one() from account_peppol

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :return: UUID to ack, wrapped in dict (e.g. {'uuid': '...'})
        """
        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']

        order_ref_id = tree.findtext('./{*}OrderReference/{*}ID')
        order = self.env['purchase.order'].search([('peppol_order_id', '=', order_ref_id)])
        if not order:
            return {}

        order_response_code = tree.findtext('./{*}OrderResponseCode')
        received_event = {
            'AB': Event.RECEIVE_AB,
            'AP': Event.RECEIVE_AP,
            'RE': Event.RECEIVE_RE,
        }[order_response_code]
        order.process_event(received_event)

        return {'uuid': uuid}

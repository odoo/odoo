from base64 import b64encode

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

    def _peppol_import_advanced_order(self, attachment, peppol_state, uuid):
        """Import documents related to advanced order. Note that for order change and order
        cancellation, they wouldn't update the order automatically. The user would need to confirm
        these requests (see sale.edi.xml.ubl_bis3_order_change.process_peppol_order_change)

        Note: ensure_one() from account_peppol

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :return: UUID to ack, wrapped in dict (e.g. {'uuid': '...'})
        """
        customization_id = {
            'order': 'urn:fdc:peppol.eu:poacc:trns:order:3',
            'order_change': 'urn:fdc:peppol.eu:poacc:trns:order_change:3',
            'order_cancel': 'urn:fdc:peppol.eu:poacc:trns:order_cancellation:3',
        }

        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']
        doc_customization_id = tree.findtext('.//{*}CustomizationID')

        if doc_customization_id == customization_id['order']:
            order = self.env['sale.order'].with_context(default_partner_id=self.env.user.partner_id.id)._create_records_from_attachments(attachment)
            order.write({
                'peppol_message_uuid': uuid,
                'peppol_order_state': peppol_state,
            })
            partner = order.partner_id.commercial_partner_id.with_company(order.company_id)
            order_response_xml = self.env['sale.edi.xml.ubl_bis3_order_response_advanced'].build_order_response_xml(order, 'AB')
            params = {
                'documents': [{
                    'filename': f"{attachment.name}-response",
                    'ubl': b64encode(order_response_xml).decode(),
                    'receiver': f"{partner.peppol_eas}:{partner.peppol_endpoint}",
                }],
            }
            self._call_peppol_proxy(
                "/api/peppol/1/send_document",
                params=params,
            )

        elif doc_customization_id == customization_id['order_change']:
            order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
            order = self.env['sale.order'].search([('peppol_order_id', '=', order_ref_id)], limit=1)
            if order:
                order.message_post(
                    body=self.env._("Received PEPPOL order change request."),
                    attachment_ids=[attachment.id],
                )
                attachment.write({'res_model': 'sale.order', 'res_id': order.id})
                order.l10n_sg_has_peppol_order_change = True

        elif doc_customization_id == customization_id['order_cancel']:
            order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
            order = self.env['sale.order'].search([('peppol_order_id', '=', order_ref_id)], limit=1)
            if order:
                order.message_post(
                    body=self.env._("Received PEPPOL order change request."),
                    attachment_ids=[attachment.id],
                )
                attachment.write({'res_model': 'sale.order', 'res_id': order.id})
                order.l10n_sg_has_peppol_order_cancel = True

        else:
            # We did not handle any document
            return {}

        return {'uuid': uuid}

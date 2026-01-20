from base64 import b64encode

from odoo import models
from odoo.tools.float_utils import float_compare
from markupsafe import Markup, escape


class Account_Edi_Proxy_ClientUser(models.Model):
    _inherit = 'account_edi_proxy_client.user'

    def _peppol_import_document(self, attachment, peppol_state, uuid, journal=None):
        """ Import PEPPOL document as either account.move or sale.order, depending on xml_tree's
        cbc:ProfileID element
        """
        self.ensure_one()

        file_data = self.env['sale.order']._to_files_data(attachment)[0]

        customization_id = file_data['xml_tree'].findtext('.//{*}CustomizationID')
        profile_id = file_data['xml_tree'].findtext('.//{*}ProfileID')

        if (
            customization_id
            in {
                'urn:fdc:peppol.eu:poacc:trns:order:3',
                'urn:fdc:peppol.eu:poacc:trns:order_change:3',
                'urn:fdc:peppol.eu:poacc:trns:order_cancellation:3',
            }
            and profile_id in {
                'urn:fdc:peppol.eu:poacc:bis:ordering:3',  # Order message (T01) must still use the standard Ordering profile identifier
                'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3',
            }
        ):
            return self._peppol_import_advanced_order(attachment, peppol_state, uuid)

        if (
            customization_id == 'urn:fdc:imda.gov.sg:trns:order_balance:1'
            and profile_id == 'urn:fdc:imda.gov.sg:bis:order_balance:1'
            ):
            return self._peppol_import_order_balance(attachment, peppol_state, uuid)

        return super()._peppol_import_document(attachment, peppol_state, uuid, journal)

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
            partner = self.env.ref('base.public_partner')
            order = self.env['sale.order'].with_context(default_partner_id=partner.id)._peppol_create_order_from_attachment(attachment)
            order.write({
                'l10n_sg_peppol_message_uuid': uuid,
            })
            attachment.write({'res_model': 'sale.order', 'res_id': order.id})
            order_tx = self.env['sale.peppol.advanced.order.transaction'].create({
                'order_id': order.id,
                'attachment_id': attachment.id,
                'state': 'to_reply',
                'document_type': 'order',
            })

            partner = order.partner_id.commercial_partner_id.with_company(order.company_id)
            order_response_xml = self.env['sale.edi.xml.ubl_bis3_order_response_advanced'].build_order_response_xml(order, order_tx, 'AB')
            params = {
                'documents': [{
                    'filename': f"{attachment.name}-response",
                    'ubl': b64encode(order_response_xml).decode(),
                    'receiver': partner.routing_identifier,
                }],
            }
            self._call_peppol_proxy(
                "/api/peppol/1/send_document",
                params=params,
            )

        elif doc_customization_id == customization_id['order_change']:
            order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
            order_change_seq = tree.findtext('.//{*}SequenceNumberID')
            document_id = tree.findtext('./{*}ID')
            order = self.env['sale.order'].search([('l10n_sg_peppol_order_id', '=', order_ref_id)], limit=1)
            if order:
                order.message_post(
                    body=self.env._("Received PEPPOL order change request."),
                    attachment_ids=[attachment.id],
                )
                attachment.write({'res_model': 'sale.order', 'res_id': order.id})
                self.env['sale.peppol.advanced.order.transaction'].create({
                    'order_id': order.id,
                    'order_change_ref': document_id,
                    'attachment_id': attachment.id,
                    'state': 'to_reply',
                    'document_type': 'order_change',
                    'sequence': order_change_seq or 0,
                })
                self.env['sale.edi.xml.ubl_bis3_order_change'].log_order_change_diff(order, tree)

        elif doc_customization_id == customization_id['order_cancel']:
            order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
            order = self.env['sale.order'].search([('l10n_sg_peppol_order_id', '=', order_ref_id)], limit=1)
            if order:
                order.message_post(
                    body=self.env._("Received PEPPOL order cancellation request."),
                    attachment_ids=[attachment.id],
                )
                self.env['sale.peppol.advanced.order.transaction'].create({
                    'order_id': order.id,
                    'attachment_id': attachment.id,
                    'state': 'to_reply',
                    'document_type': 'order_cancel',
                })
                attachment.write({'res_model': 'sale.order', 'res_id': order.id})

        else:
            return {}

        return {'uuid': uuid}

    def _peppol_import_order_balance(self, attachment, peppol_state, uuid):
        """Receive an order balance document indicating remaining quantities per order line.

        This method does NOT automatically update order quantities or other data. It only
        appends received notes to the order and order lines as a notification. The user
        must review the chatter and manually act on the balance information.

        Lines with zero or negative remaining quantity are skipped; only lines with
        outstanding balance are included in the chatter summary.

        :param attachment: the new document
        :param peppol_state: the state of the received Peppol document
        :param uuid: the UUID of the Peppol document
        :return: UUID to ack, wrapped in dict (e.g. {'uuid': '...'})
        """
        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']

        order_ref_id = tree.findtext('.//{*}OrderDocumentReference/{*}ID')
        if order_ref_id is None:
            return {}

        order = self.env['sale.order'].search([('l10n_sg_peppol_order_id', '=', order_ref_id)], limit=1)
        if not order:
            return {}

        attachment.write({'res_model': 'sale.order', 'res_id': order.id})

        document_id = tree.findtext('./{*}ID')
        note_prefix = f'[{document_id}] ' if document_id else ''

        doc_note = tree.findtext('./{*}Note')
        if doc_note:
            prefixed_note = note_prefix + doc_note
            current_note = order.note or ''
            order.note = f'{current_note}\n{prefixed_note}' if current_note else prefixed_note

        log = Markup()
        for order_line_node in tree.findall('./{*}OrderLine'):
            line = order_line_node.find('./{*}LineItem')
            if line is None:
                continue
            line_id = line.findtext('./{*}ID')
            order_line = order.order_line.filtered(lambda l: l.l10n_sg_ubl_line_item_ref == line_id)
            if not order_line:
                continue
            quantity = float(line.findtext('./{*}Quantity'))
            if float_compare(quantity, 0, precision_rounding=order_line.product_uom_id.rounding) <= 0:
                continue

            log += Markup("<li>%s: %s %s</li>") % (
                escape(order_line.product_id.display_name),
                quantity,
                escape(order_line.product_uom_id.name),
            )

            line_note = order_line_node.findtext('./{*}Note')
            if line_note:
                prefixed_line_note = note_prefix + line_note
                current_line_name = order_line.name or ''
                order_line.name = f'{current_line_name}\n{prefixed_line_note}' if current_line_name else prefixed_line_note

        customer_ref = tree.findtext('./{*}CustomerReference')
        msg = Markup("<b>Received PEPPOL order balance (ID: %s, Customer Reference: %s)</b>") % (document_id, customer_ref)
        if log:
            msg += Markup("<ul>") + log + Markup("</ul>")
        order.message_post(body=msg)

        return {'uuid': uuid}

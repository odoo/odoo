from markupsafe import Markup

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
        """Import documents related to advanced order:
        - Order: create new order
        - Order Change: update matching order
        - Order Cancellation: set order state to cancelled
        - Order Balance: add indication on order lines

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
        elif doc_customization_id == customization_id['order_change']:
            order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
            order = self.env['sale.order'].search([('peppol_order_id', '=', order_ref_id)])
            if order:
                order_vals, logs = self.env['sale.edi.xml.ubl_bis3_advanced_order']._retrieve_order_vals(order, tree)
                order_change_seq_no = order_vals.get('order_change_seq_no')
                if order_change_seq_no and order_change_seq_no <= order.peppol_order_change_seq:
                    order.message_post(self.env._("Received invalid order change sequence number:"
                                                  " %s. Rejecting the order change message.",
                                                  order_change_seq_no))
                    # Return rejection order response
                    return {}
                order.peppol_order_change_seq = order_change_seq_no
                order.client_order_ref = f"{order_ref_id}-{order_change_seq_no}"
                for order_line in order_vals['order_line']:
                    # order_vals['order_line'] is a Command.create tuple (i.e. (6, 0, values_dict))
                    # Maybe we can refactor _retrieve_order_vals > _import_lines so we can use the
                    # method outside of _retrieve_order_vals as well.
                    order_line_vals = order_line[2]
                    line_status_code = order_line_vals.pop('line_status_code', None)

                    if line_status_code == "1":  # Line is being added
                        pass
                    elif line_status_code == "2":  # Line is being deleted
                        updated_line_ref = order_line_vals.get('ubl_line_item_ref')
                        if updated_line_ref is None:
                            continue
                        order.order_line.search(
                            [('ubl_line_item_ref', '=', updated_line_ref)],
                            limit=1,
                        ).unlink()
                    elif line_status_code == "3":  # Line is being updated
                        updated_line_ref = order_line_vals.get('ubl_line_item_ref')
                        if updated_line_ref is None:
                            continue
                        line_to_update = order.order_line.search(
                            [('ubl_line_item_ref', '=', updated_line_ref)],
                            limit=1,
                        )
                        # Unlink and rewrite line level charges
                        line_to_update['linked_line_ids'].unlink()
                        line_to_update.write(order_line_vals)
                order.message_post(body=Markup("<strong>%s</strong>") % self.env._("Format used to import the document: %s", self._description))
                if logs:
                    order._create_activity_set_details(Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % l for l in logs))
        elif doc_customization_id == customization_id['order_cancel']:
            order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
            order = self.env['sale.order'].search([('peppol_order_id', '=', order_ref_id)])
            if order:
                order.state = 'cancel'
        else:
            # We did not handle any document
            return {}

        return {'uuid': uuid}

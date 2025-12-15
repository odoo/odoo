import os

from lxml import etree
from markupsafe import Markup

from odoo import models
from odoo.exceptions import UserError, ValidationError

from odoo.addons.account.tools import dict_to_xml
from odoo.addons.sale_peppol.tools import OrderResponse


class SaleEdiXmlUbl_Bis3_AdvancedOrder(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_advanced_order'
    _inherit = ['sale.edi.xml.ubl_bis3']
    _description = "Sale BIS Advanced Ordering 3.0"

    # -------------------------------------------------------------------------
    # Order import common
    # -------------------------------------------------------------------------

    def _retrieve_order_vals(self, order, tree):
        """ OVERRIDE of `sale_edi_ubl.sale.edi.xml.ubl_bis3` to retrieve advanced order values
            from incoming order documents
        """
        order_vals, logs = super()._retrieve_order_vals(order, tree)

        # For advanced orders, use peppol_order_id as a readonly reference to match documents.
        order_vals['peppol_order_id'] = order_vals.pop('client_order_ref')

        # Reference ID for order change and cancellation documents
        order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
        if order_ref_id is not None:
            order_vals['order_ref_id'] = order_ref_id

        return order_vals, logs

    def _retrieve_line_vals(self, tree, document_type=False, qty_factor=1):
        """Override of `account.edi.common` to adapt dictionary keys from the base method to be
        compatible with the `sale.order.line` model."""
        xpath_dict = self._get_line_xpaths(document_type, qty_factor)

        line_item_id = None
        line_item_id_node = tree.find(xpath_dict['line_item_id'])
        if line_item_id_node is not None:
            line_item_id = line_item_id_node.text

        return {
            'ubl_line_item_ref': line_item_id,
            **super()._retrieve_line_vals(tree, document_type, qty_factor),
        }

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        """OVERRIDE of `account.edi.xml.ubl_bis3` to update dictionary key used for extracting
        document line item ID. This is crucial for advanced order to match line items to update on
        order change request.
        """
        return {
            **super()._get_line_xpaths(document_type=document_type, qty_factor=qty_factor),
            'line_item_id': './{*}ID',
        }

    # -------------------------------------------------------------------------
    # Order export common
    # -------------------------------------------------------------------------
    def _get_document_nsmap(self, vals):
        return {
            None: {
                'order': "urn:oasis:names:specification:ubl:schema:xsd:Order-2",
                'order_change': "urn:oasis:names:specification:ubl:schema:xsd:OrderChange-2",
                'order_cancel': "urn:oasis:names:specification:ubl:schema:xsd:OrderCancellation-2",
                'order_response_advanced': "urn:oasis:names:specification:ubl:schema:xsd:OrderResponse-2",
            }[vals['document_type']],
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        }


class SaleEdiXmlUbl_Bis3_OrderChange(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_order_change'
    _inherit = ['sale.edi.xml.ubl_bis3_advanced_order']
    _description = "Peppol Order Change transaction 3.1"

    # -------------------------------------------------------------------------
    # Order change EDI import
    # -------------------------------------------------------------------------

    def _retrieve_line_vals(self, tree, document_type=False, qty_factor=1):
        """Override of `account.edi.common` to adapt dictionary keys from the base method to be
        compatible with the `sale.order.line` model."""
        xpath_dict = self._get_line_xpaths(document_type, qty_factor)

        line_status_code = None
        line_status_code_node = tree.find(xpath_dict['line_status_code'])
        if line_status_code_node is not None:
            line_status_code = line_status_code_node.text

        return {
            'line_status_code': line_status_code,
            **super()._retrieve_line_vals(tree, document_type, qty_factor),
        }

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        """OVERRIDE of `sale.edi.xml.ubl_bis3_advanced_order` to update dictionary key used for
        extracting order change lines' status code
        """
        return {
            **super()._get_line_xpaths(document_type=document_type, qty_factor=qty_factor),
            'line_status_code': './{*}LineStatusCode',
        }

    def process_peppol_order_change(self, order):
        """ Apply PEPPOL order change document to `sale_order`. Searches through ir.attachment of
        the order and applies the latest PEPPOL order change document.
        """
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', order.id),
        ])
        customization_target = 'urn:fdc:peppol.eu:poacc:trns:order_change:3'
        order_change_attachments = attachments.filtered(lambda a: (
            (self.env['sale.order']._to_files_data(a)[0].get('xml_tree').findtext('.//{*}CustomizationID')
             if a else None) == customization_target
        ))
        attachment = order_change_attachments[0]  # Last received PEPPOL document attachment; attachments are ordered as id desc
        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']

        order_vals, logs = self._retrieve_order_vals(order, tree)
        order.peppol_order_change_id = order_vals['peppol_order_id']

        for order_line in order_vals['order_line']:
            # order_vals['order_line'] is a Command.create tuple (i.e. (0, 0, values_dict))
            # Maybe we can refactor _retrieve_order_vals > _import_lines so we can use the
            # method outside of _retrieve_order_vals as well.
            order_line_vals = order_line[2]
            line_status_code = order_line_vals.pop('line_status_code', None)

            if line_status_code == "1":  # Line is being added
                order.write({'order_line': [order_line]})

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
                line_to_update = next(filter(
                    lambda line: line.ubl_line_item_ref == updated_line_ref,
                    order.order_line,
                ), None)
                if line_to_update:
                    line_to_update['linked_line_ids'].unlink()
                    line_to_update.write(order_line_vals)
                else:
                    logs.append(self.env._(
                        "Failed to apply line changes because order line with line item reference"
                        " %s is not found.", updated_line_ref,
                    ))

        order.message_post(body=self.env._("Applied PEPPOL order change document"))
        order.message_post(body=Markup("<strong>%s</strong>") % self.env._("Format used to import the document: %s", self._description))
        if logs:
            order._create_activity_set_details(Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % log for log in logs))


class SaleEdiXmlUbl_Bis3_OrderCancel(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_order_cancel'
    _inherit = ['sale.edi.xml.ubl_bis3_advanced_order']
    _description = "Peppol Order Cancellation transaction 3.0"

    # -------------------------------------------------------------------------
    # Order cancellation EDI import
    # -------------------------------------------------------------------------

    def _retrieve_order_vals(self, order, tree):
        order_vals, logs = super()._retrieve_order_vals(order, tree)
        order_vals['cancellation_note'] = tree.findtext('./{*}CancellationNote')

        return order_vals, logs

    def process_peppol_order_cancel(self, order):
        """ Apply PEPPOL order cancellation document to `sale_order`. Searches through ir.attachment
        of the order and applies PEPPOL document with highest sequence (`cbc:SequenceNumberID`)
        """
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'sale.order'),
            ('res_id', '=', order.id),
        ])
        customization_target = 'urn:fdc:peppol.eu:poacc:trns:order_cancellation:3'
        order_cancel_attachments = attachments.filtered(lambda a: (
            (self.env['sale.order']._to_files_data(a)[0].get('xml_tree').findtext('.//{*}CustomizationID')
             if a else None) == customization_target
        ))
        if not order_cancel_attachments:
            raise UserError(self.env._("There is no order cancellation request document related to this order."))
        attachment = order_cancel_attachments[0]  # Last received PEPPOL document attachment; attachments are ordered as id desc

        # Call cancellation first to check for UserError
        order.action_cancel()

        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']

        order_vals, logs = self._retrieve_order_vals(order, tree)
        msg = "Applied PEPPOL order cancellation document"
        if order_vals['cancellation_note']:
            msg = f"{msg}: {order_vals['cancellation_note']}"

        order.message_post(body=self.env._(msg))
        order.message_post(body=Markup("<strong>%s</strong>") % self.env._("Format used to import the document: %s", self._description))
        if logs:
            order._create_activity_set_details(Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % log for log in logs))


class SaleEdiXmlUbl_Bis3_OrderResponseAdvanced(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_order_response_advanced'
    _inherit = ['sale.edi.xml.ubl_bis3_advanced_order']
    _description = "Peppol Order Response Advanced transaction 3.1"

    # -------------------------------------------------------------------------
    # Order Response Advanced EDI export
    # -------------------------------------------------------------------------

    def _get_order_response_node(self, vals, response_code):
        code_list = [
            'AB',  # Ack
            'AP',  # Accepted
        ]
        if response_code not in code_list:
            raise ValidationError(self.env._("Unknown response code %s", response_code))

        self._add_sale_order_config_vals(vals)
        self._add_sale_order_currency_vals(vals)

        document_node = {}
        self._add_sale_order_header_nodes(document_node, vals)
        document_node['cbc:OrderResponseCode'] = {'_text': response_code}
        self._add_sale_order_seller_supplier_party_nodes(document_node, vals)
        self._add_sale_order_buyer_customer_party_nodes(document_node, vals)
        self._add_sale_order_delivery_nodes(document_node, vals)
        # TODO: Order response with code CA (Conditionally Accepted) would require cac:OrderLine

        return document_node

    def _add_sale_order_config_vals(self, vals):
        super()._add_sale_order_config_vals(vals)
        vals.update({'document_type': 'order_response_advanced'})

    def _add_sale_order_header_nodes(self, document_node, vals):
        super()._add_sale_order_header_nodes(document_node, vals)
        sale_order = vals['sale_order']
        document_node.update({
            'cbc:CustomizationID': {'_text': 'urn:fdc:peppol.eu:poacc:trns:order_response_advanced:3'},
            'cbc:ProfileID': {'_text': 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'},  # Move to parent (common) if used in other documents
            'cbc:OrderResponseCode': {'_text': 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'},
            'cac:OrderReference': {
                'cbc:ID': {'_text': sale_order.peppol_order_id},
            },
        })
        document_node.pop('cbc:OrderTypeCode')
        document_node.pop('cac:ValidityPeriod')
        document_node.pop('cac:OriginatorDocumentReference')

        if sale_order.peppol_order_change_id:
            document_node['cac:OrderChangeDocumentReference'] = {
                'cbc:ID': {'_text': sale_order.peppol_order_change_id},
            }

    def _get_party_node(self, vals):
        """ Override of `account.edi.xml.ubl_bis3`. Creates seller and buyer party node dict.
        """
        # Similar to UBL BIS3 Order export, but omitted child nodes make inheritance impractical.
        # Logic rewritten to avoid complex overrides.
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id

        party_node = {
            'cac:PartyIdentification': {
                'cbc:ID': {'_text': commercial_partner.ref},
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
            },
        }

        if commercial_partner.peppol_endpoint:
            party_node['cbc:EndpointID'] = {
                '_text': commercial_partner.peppol_endpoint,
                'schemeID': commercial_partner.peppol_eas,
            }

        return party_node

    def _add_sale_order_delivery_nodes(self, document_node, vals):
        sale_order = vals['sale_order']

        if sale_order.commitment_date:
            date_str = sale_order.commitment_date.strftime("%Y-%m-%d")
            time_str = sale_order.commitment_date.strftime("%H:%M:%S")

            document_node['cac:Delivery'] = {
                'cac:PromisedDeliveryPeriod': {
                    'cbc:EndDate': {'_text': date_str},
                    'cbc:EndTime': {'_text': time_str},
                },
            }

    def build_order_response_xml(self, order, response_code):
        # TODO: Create constraint on creating order response. The PEPPOL endpoint ID of buyer should
        # be handled by order import. Since the recepient needs to have PEPPOL id to receive the
        # order this shouldn't really be a problem, it's just nice to have
        vals = {'sale_order': order}
        document_node = self._get_order_response_node(vals, response_code)
        xml_content = dict_to_xml(document_node, nsmap=self._get_document_nsmap(vals), template=OrderResponse)

        xml_bytes = etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8')
        filename = "test_wopy.xml"
        file_path = os.path.join('/home/odoo/workspace/sg-peppol-order-balance/odoo/addons/sale_peppol/tests/assets', filename)

        # Write file and return its path
        with open(file_path, 'wb') as f:
            f.write(xml_bytes)

        return xml_bytes
        # return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8')

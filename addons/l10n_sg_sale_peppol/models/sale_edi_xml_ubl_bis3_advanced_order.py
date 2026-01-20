from lxml import etree
from markupsafe import Markup, escape

from odoo import models, Command
from odoo.exceptions import ValidationError

from odoo.addons.account.tools import dict_to_xml
from odoo.addons.l10n_sg_sale_peppol.tools import OrderResponse


class SaleEdiXmlUbl_Bis3_AdvancedOrder(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_advanced_order'
    _inherit = 'sale.edi.xml.ubl_bis3'
    _description = "Sale BIS Advanced Ordering 3.0"

    # -------------------------------------------------------------------------
    # Order import
    # -------------------------------------------------------------------------

    def _retrieve_order_vals(self, order, tree):
        """ OVERRIDE of `sale_edi_ubl.sale.edi.xml.ubl_bis3` to retrieve advanced order values
            from incoming order documents
        """
        order_vals, logs = super()._retrieve_order_vals(order, tree)

        # The parent module `sale_edi_ubl` imports the document ID as client_order_ref field. The SG
        # government requirement specifies the customer reference value (cbc:CustomerReference) to
        # be available on the SO. Also the customer reference value should be persisted when the SO
        # is flipped to invoice, which makes client_order_ref field ideal for storing this value.
        document_id = tree.findtext('./{*}ID')
        order_vals['l10n_sg_peppol_order_id'] = document_id
        order_vals['client_order_ref'] = tree.findtext('./{*}CustomerReference')
        note_prefix = f'[{document_id}] ' if document_id else ''

        # Compare buyer contact info from the document against the matched Odoo partner.
        # VAT/endpoint drives partner lookup, so the contact node may carry different values.
        # When there is a discrepancy, try to resolve it to the correct sub-contact:
        #   1. Search for an existing child of the commercial partner matching the XML contact.
        #   2. If none, create one (only possible under a company partner, not an individual).
        #   3. If neither is possible, fall back to logging the discrepancy.
        contact_name = tree.findtext('./{*}BuyerCustomerParty/{*}Party/{*}Contact/{*}Name')
        contact_email = tree.findtext('./{*}BuyerCustomerParty/{*}Party/{*}Contact/{*}ElectronicMail')
        partner_id = order_vals.get('partner_id')
        if (contact_name or contact_email) and partner_id:
            partner = self.env['res.partner'].browse(partner_id)
            name_mismatch = bool(contact_name and contact_name != partner.name)
            email_mismatch = bool(contact_email and contact_email != (partner.email or ''))
            if name_mismatch or email_mismatch:
                commercial_partner = partner.commercial_partner_id
                if contact_email:
                    sub_contact = self.env['res.partner'].search(
                        [('parent_id', '=', commercial_partner.id),
                         ('email', '=', contact_email),
                         ('name', '=', contact_name)],
                        limit=1,
                    )
                else:
                    sub_contact = self.env['res.partner'].search(
                        [('parent_id', '=', commercial_partner.id)],
                        limit=1,
                    )

                if sub_contact:
                    order_vals['partner_id'] = sub_contact.id
                elif commercial_partner.is_company and contact_name:
                    sub_contact = self.env['res.partner'].create({
                        'name': contact_name,
                        'email': contact_email,
                        'parent_id': commercial_partner.id,
                        'type': 'contact',
                    })
                    order_vals['partner_id'] = sub_contact.id
                    order._message_log(body=Markup("<b>%s</b>") % self.env._(
                        "Created new sub-contact '%(contact_name)s' under '%(company_name)s' from buyer contact info.",
                        contact_name=contact_name, company_name=commercial_partner.display_name,
                    ))
                else:
                    # Individual partner or no contact name — cannot create a sub-contact; log instead.
                    discrepancies = []
                    if name_mismatch:
                        discrepancies.append(self.env._("Name: %s", contact_name))
                    if email_mismatch:
                        discrepancies.append(self.env._("Email: %s", contact_email))
                    order._message_log(body=Markup("<b>%s</b><ul>%s</ul>") % (
                        self.env._("Buyer contact info from document differs from Odoo contact:"),
                        Markup().join(Markup("<li>%s</li>") % d for d in discrepancies),
                    ))

        # Note: The parent module `sale_edi_ubl` drops the 'note' element from `order_vals`.
        # In case there is default T&C template for SO, we append the Note text from the UBL
        doc_note = tree.findtext('./{*}Note')
        if doc_note:
            existing_note = str(order.note) if order.note else ''
            prefixed_note = note_prefix + doc_note
            order_vals['note'] = f'{existing_note}\n{prefixed_note}' if existing_note else prefixed_note

        # Reference ID for order change and cancellation documents
        order_ref_id = tree.findtext('.//{*}OrderReference/{*}ID')
        if order_ref_id is not None:
            order_vals['order_ref_id'] = order_ref_id

        for order_line_node in tree.findall('./{*}OrderLine'):
            line_item = order_line_node.find('./{*}LineItem')
            if line_item is None:
                continue
            line_note = order_line_node.findtext('./{*}Note')
            if not line_note:
                continue
            line_id = line_item.findtext('./{*}ID')
            for line_cmd in order_vals.get('order_line', []):
                if line_cmd[2].get('l10n_sg_ubl_line_item_ref') == line_id:
                    existing_name = line_cmd[2].get('name') or ''
                    prefixed_note = note_prefix + line_note
                    line_cmd[2]['name'] = f'{existing_name}\n{prefixed_note}' if existing_name else prefixed_note
                    break

        return order_vals, logs

    def _retrieve_line_vals(self, record, tree, document_type=False, qty_factor=1):
        """
        EXTENSION of `sale.edi.xml.ubl_bis3` module. Adds 'line_item_id' which is used to identify
        order lines when importing/exporting orders to PEPPOL advanced document.
        """
        xpath_dict = self._get_line_xpaths(document_type, qty_factor)

        line_item_id = None
        line_item_id_node = tree.find(xpath_dict['line_item_id'])
        if line_item_id_node is not None:
            line_item_id = line_item_id_node.text

        line_vals = {
            'l10n_sg_ubl_line_item_ref': line_item_id,
            **super()._retrieve_line_vals(record, tree, document_type, qty_factor),
        }

        delivery_note = self._get_line_delivery_period_note(tree)
        if delivery_note:
            existing_name = line_vals.get('name') or ''
            line_vals['name'] = '\n'.join(filter(None, [existing_name, delivery_note]))

        return line_vals

    def _get_line_delivery_period_note(self, tree):
        """Parse cac:RequestedDeliveryPeriod from a LineItem tree node and return a human-readable
        string, or an empty string if the element is absent."""
        period_node = tree.find('./{*}Delivery/{*}RequestedDeliveryPeriod')
        if period_node is None:
            return ''

        start_date = period_node.findtext('./{*}StartDate') or ''
        start_time = period_node.findtext('./{*}StartTime') or ''
        end_date = period_node.findtext('./{*}EndDate') or ''
        end_time = period_node.findtext('./{*}EndTime') or ''

        start = ' '.join(filter(None, [start_date, start_time]))
        end = ' '.join(filter(None, [end_date, end_time]))

        if start and end:
            return self.env._("Requested Delivery Period: %(start)s - %(end)s", start=start, end=end)
        if start:
            return self.env._("Requested Delivery From: %s", start)
        if end:
            return self.env._("Requested Delivery By: %s", end)
        return ''

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        """OVERRIDE of `account.edi.xml.ubl_bis3` to update dictionary key used for extracting
        document line item ID. This is crucial for advanced order to match line items to update on
        order change request.
        """
        return {
            **super()._get_line_xpaths(document_type=document_type, qty_factor=qty_factor),
            'line_item_id': './{*}ID',
            'delivered_qty': './{*}Quantity',
        }

    def _import_lines(self, record, tree, xpath, document_type=False, tax_type=False, qty_factor=1):
        """ OVERRIDE of `sale_edi_ubl` to create linkage from order lines to their related
            charge lines, needed so `process_peppol_order_change` can clear stale charge
            lines when a line is updated via an Order Change document.
        """
        logs = []
        lines_values = []
        for line_tree in tree.iterfind(xpath):
            line_values = self.with_company(record.company_id)._retrieve_line_vals(record, line_tree, document_type, qty_factor)
            line_values['tax_ids'], tax_logs = self._retrieve_taxes(record, line_values, tax_type)
            logs += tax_logs
            if not line_values['product_uom_id']:
                line_values.pop('product_uom_id')  # if no uom, pop it so it's inferred from the product_id
            charge_lines_values = self._retrieve_line_charges(record, line_values, line_values['tax_ids'])
            line_values['linked_line_ids'] = [Command.create({
                    'order_id': record.id,
                    **charge_line_values,
                }) for charge_line_values in charge_lines_values]
            lines_values.append(line_values)
        return lines_values, logs

    # -------------------------------------------------------------------------
    # Order export
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

    def _ubl_add_seller_supplier_party_node(self, vals):
        """
        EXTENDS `account.edi.ubl`. The seller supplier party should not have 'cac:PartyTaxScheme'.
        """
        super()._ubl_add_seller_supplier_party_node(vals)
        party_node = vals['document_node']['cac:SellerSupplierParty']['cac:Party']
        party_node.pop('cac:PartyTaxScheme', None)

    def _ubl_add_party_identification_nodes(self, vals):
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        vals['party_node']['cac:PartyIdentification'] = [{
            'cbc:ID': {
                '_text': commercial_partner.routing_endpoint,
                'schemeID': commercial_partner.routing_scheme or None,
            },
        }]

    def _peppol_import_order_ubl(self, order, file_data, new):
        """
        PEPPOL-specific import: bypass the price unit computation of the created order lines.
        Used only when importing from PEPPOL AP; manual file import uses _import_order_ubl (parent).
        """
        tree = file_data['xml_tree']

        # Update the order.
        order_vals, logs = self._retrieve_order_vals(order, tree)
        if order:
            # currency_id must be written separately: writing partner_id in the same call triggers
            # _compute_pricelist_id → _compute_currency_id, which overrides any currency_id written
            # in the same write() with the pricelist's currency (typically the company currency).
            currency_id = order_vals.pop('currency_id', None)
            order.write(order_vals)
            if currency_id:
                order.write({'currency_id': currency_id})
            doc_id = order_vals.get('l10n_sg_peppol_order_id')
            msg = Markup("<strong>%s</strong>") % self.env._("Format used to import the document: %s", self._description)
            if doc_id:
                msg += Markup("<strong> (ID: %s)</strong>") % escape(doc_id)
            order.message_post(body=msg)
            if logs:
                order._create_activity_set_details(Markup("<ul>%s</ul>") % Markup().join(Markup("<li>%s</li>") % log for log in logs))


class SaleEdiXmlUbl_Bis3_OrderChange(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_order_change'
    _inherit = ['sale.edi.xml.ubl_bis3_advanced_order']
    _description = "Peppol Order Change transaction 3.1"

    # -------------------------------------------------------------------------
    # Order change EDI import
    # -------------------------------------------------------------------------

    def _retrieve_line_vals(self, record, tree, document_type=False, qty_factor=1):
        """
        EXTENSION of `sale.edi.xml.ubl_bis3_advanced_order` module. Adds 'line_status_code' in
        'order change' document import. The code is used to identify whether the lines are added,
        deleted, changed, or unchanged.
        """
        line_status_code = None
        line_status_code_node = tree.find('./{*}LineStatusCode')
        if line_status_code_node is not None:
            line_status_code = line_status_code_node.text

        return {
            'line_status_code': line_status_code,
            **super()._retrieve_line_vals(record, tree, document_type, qty_factor),
        }

    def log_order_change_diff(self, order, tree):
        """
        Compare the order's order line data with the tree's order line data then log the difference.
        This is to help users to know what the incoming changes are about.
        """
        doc_id = tree.findtext('./{*}ID')
        html_output = Markup("<b>Received order change request via PEPPOL")
        if doc_id:
            html_output += Markup(" (ID: %s)") % escape(doc_id)
        html_output += Markup(":</b><ul>")
        for line_tree in tree.iterfind('./{*}OrderLine/{*}LineItem'):
            line_vals = self._retrieve_line_vals(order, line_tree)
            line_status_code = line_vals.pop('line_status_code')
            if line_status_code == '1':
                html_output += Markup("<li>Line added: %s</li>") % escape(line_vals['name'])
                html_output += Markup("<ul>")
                html_output += Markup("<li>Quantity: %s</li>") % line_vals['product_uom_qty']
                html_output += Markup("<li>Unit Price: %s</li>") % line_vals['price_unit']
                if line_vals['discount'] != 0:
                    html_output += Markup("<li>Discount %s</li>") % line_vals['discount']
                html_output += Markup("</ul>")
                continue

            updated_line_ref = line_vals.pop('l10n_sg_ubl_line_item_ref')
            line = order.order_line.search(
                    [('l10n_sg_ubl_line_item_ref', '=', updated_line_ref)],
                    limit=1,
                )
            if not line:
                continue

            if line_status_code == '2':  # Order line is deleted
                html_output += Markup("<li>Line deleted: %s</li>") % escape(line.name)
            elif line_status_code == '3':  # Order line is changed
                currency = order.currency_id

                html_output += Markup("<li>Line changed: %s</li>") % escape(line.name)
                html_output += Markup("<ul>")

                if line.product_id.id != line_vals['product_id']:
                    html_output += Markup("<li>Product ID: %s -> %s</li>") % (
                        line.product_id.id,
                        line_vals['product_id'],
                    )
                if line.product_uom_qty != line_vals['product_uom_qty']:
                    html_output += Markup("<li>Quantity: %s -> %s</li>") % (
                        line.product_uom_qty,
                        line_vals['product_uom_qty'],
                    )
                if currency.compare_amounts(line.price_unit, line_vals['price_unit']) != 0:
                    html_output += Markup("<li>Unit Price: %s -> %s</li>") % (
                        line.price_unit,
                        line_vals['price_unit'],
                    )
                if currency.compare_amounts(line.discount, line_vals['discount']) != 0:
                    html_output += Markup("<li>Discount: %s -> %s</li>") % (
                        line.discount,
                        currency.round(line_vals['discount']),
                    )

                html_output += Markup("</ul>")

        html_output += Markup("</ul>")
        order.message_post(body=html_output)

    def process_peppol_order_change(self, order, attachment):
        """
        Apply PEPPOL order change document to `sale_order`. Searches through the sale order's
        PEPPOL transactions and apply the most recent order change request to the order.
        """
        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']
        order_vals, logs = self._retrieve_order_vals(order, tree)

        for order_line in order_vals['order_line']:
            # order_vals['order_line'] is a Command.create tuple (i.e. (0, 0, values_dict))
            order_line_vals = order_line[2]
            line_status_code = order_line_vals.pop('line_status_code', None)

            if line_status_code == "1":  # Line is being added
                order.write({'order_line': [order_line]})

            elif line_status_code == "2":  # Line is being deleted
                updated_line_ref = order_line_vals.get('l10n_sg_ubl_line_item_ref')
                if updated_line_ref is None:
                    continue
                order.order_line.search(
                    [('l10n_sg_ubl_line_item_ref', '=', updated_line_ref)],
                    limit=1,
                ).unlink()

            elif line_status_code == "3":  # Line is being updated
                updated_line_ref = order_line_vals.get('l10n_sg_ubl_line_item_ref')
                if updated_line_ref is None:
                    continue
                line_to_update = next(filter(
                    lambda line: line.l10n_sg_ubl_line_item_ref == updated_line_ref,
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

        doc_id = order_vals.get('l10n_sg_peppol_order_id')
        body = self.env._("Applied PEPPOL order change document")
        if doc_id:
            body = Markup("%s (ID: %s)") % (body, escape(doc_id))
        order.message_post(body=body)
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

    def process_peppol_order_cancel(self, order, attachment):
        """
        Apply PEPPOL order cancellation document to `sale_order`. Searches through the sale order's
        PEPPOL transactions and apply the most recent order cancellation request to the order.
        """
        # Call cancellation first to check for any UserError
        order.action_cancel()

        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']
        order_vals, logs = self._retrieve_order_vals(order, tree)
        if order_vals['cancellation_note']:
            msg = self.env._("Applied PEPPOL order cancellation document: %s", order_vals['cancellation_note'])
        else:
            msg = self.env._("Applied PEPPOL order cancellation document")

        doc_id = order_vals.get('l10n_sg_peppol_order_id')
        if doc_id:
            msg = Markup("%s (ID: %s)") % (msg, escape(doc_id))
        order.message_post(body=msg)
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

    def _get_order_response_node(self, vals):
        self._add_sale_order_config_vals(vals)
        self._add_sale_order_currency_vals(vals)

        document_node = {}
        self._add_sale_order_header_nodes(document_node, vals)
        self._add_sale_order_seller_supplier_party_nodes(document_node, vals)
        self._add_sale_order_buyer_customer_party_nodes(document_node, vals)
        self._add_sale_order_delivery_nodes(document_node, vals)

        return document_node

    def _add_sale_order_config_vals(self, vals):
        super()._add_sale_order_config_vals(vals)
        vals.update({'document_type': 'order_response_advanced'})

    def _add_sale_order_header_nodes(self, document_node, vals):
        super()._add_sale_order_header_nodes(document_node, vals)
        sale_order = vals['sale_order']
        order_tx = vals['order_tx']
        response_code = vals['response_code']
        if response_code not in ['AB', 'AP', 'CA', 'RE']:
            raise ValidationError(self.env._("Unknown response code %s", response_code))

        document_node.update({
            'cbc:ID': {'_text': f"{sale_order.name}-{order_tx.document_type}-response-{order_tx.id}"},
            'cbc:CustomizationID': {'_text': 'urn:fdc:peppol.eu:poacc:trns:order_response_advanced:3'},
            'cbc:ProfileID': {'_text': 'urn:fdc:peppol.eu:poacc:bis:advanced_ordering:3'},
            'cbc:OrderResponseCode': {'_text': response_code},
            'cac:OrderReference': {
                'cbc:ID': {'_text': sale_order.l10n_sg_peppol_order_id},
            },
        })
        document_node.pop('cbc:OrderTypeCode')
        document_node.pop('cac:ValidityPeriod')
        document_node.pop('cac:OriginatorDocumentReference')

        if order_tx.document_type == 'order_change' and order_tx.order_change_ref:
            document_node['cac:OrderChangeDocumentReference'] = {
                'cbc:ID': {'_text': order_tx.order_change_ref},
            }

    def _ubl_add_seller_supplier_party_node(self, vals):
        """
        OVERRIDE of `account.edi.ubl`. The seller supplier party should not have 'cac:PartyTaxScheme'.
        """
        node = vals['document_node']['cac:SellerSupplierParty'] = {'cac:Party': {}}
        party_node = node['cac:Party']
        sub_vals = {
            **vals,
            'party_vals': {'partner': vals['supplier']},
            'party_node': party_node,
        }
        self._ubl_add_accounting_supplier_party_endpoint_id_node(sub_vals)
        self._ubl_add_accounting_supplier_party_identification_nodes(sub_vals)
        self._ubl_add_accounting_supplier_party_legal_entity_nodes(sub_vals)

    def _ubl_add_buyer_customer_party_node(self, vals):
        """
        OVERRIDE of `account.edi.ubl`. The buyer customer party should not have 'cac:PartyTaxScheme'.
        """
        node = vals['document_node']['cac:BuyerCustomerParty'] = {'cac:Party': {}}
        party_node = node['cac:Party']
        sub_vals = {
            **vals,
            'party_vals': {'partner': vals['customer']},
            'party_node': party_node,
        }
        self._ubl_add_accounting_supplier_party_endpoint_id_node(sub_vals)
        self._ubl_add_accounting_supplier_party_identification_nodes(sub_vals)
        self._ubl_add_accounting_supplier_party_legal_entity_nodes(sub_vals)

    def _ubl_add_party_legal_entity_nodes(self, vals):
        """
        OVERRIDE of `account.edi.ubl`. Order response advanced's party legal entity should only have
        'cbc:RegistrationName'.
        """
        nodes = vals['party_node']['cac:PartyLegalEntity'] = []
        commercial_partner = vals['party_vals']['partner'].commercial_partner_id

        nodes.append({
            'cbc:RegistrationName': {'_text': commercial_partner.name},
        })

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

    def build_order_response_xml(self, order, order_tx, response_code):
        vals = {
            'sale_order': order,
            'order_tx': order_tx,
            'response_code': response_code,
        }
        document_node = self._get_order_response_node(vals)
        xml_content = dict_to_xml(document_node, nsmap=self._get_document_nsmap(vals), template=OrderResponse)

        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8')

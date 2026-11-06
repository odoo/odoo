from datetime import UTC, datetime
from zoneinfo import ZoneInfo

from lxml import etree
from markupsafe import Markup, escape

from odoo import models, Command
from odoo.exceptions import ValidationError
from odoo.tools.sql import escape_like_value

from odoo.addons.account.tools import dict_to_xml
from odoo.addons.l10n_sg_sale_peppol.tools import OrderResponse


def normalize_text(value):
    return ' '.join(str(value or '').split()).casefold()


class SaleEdiXmlUbl_Bis3_AdvancedOrder(models.AbstractModel):
    _name = 'sale.edi.xml.ubl_bis3_advanced_order'
    _inherit = 'sale.edi.xml.ubl_bis3'
    _description = "Sale BIS Advanced Ordering 3.0"

    # -------------------------------------------------------------------------
    # Order import
    # -------------------------------------------------------------------------

    def _retrieve_partner_from_endpoint(self, company, routing_scheme, routing_endpoint):
        """ Return the company partner whose Peppol ID is the EndpointID of the document, or an empty
        recordset when no partner or several partners have it.
        """
        ResPartner = self.env['res.partner']
        if not (routing_scheme and routing_endpoint):
            return ResPartner
        partners = ResPartner.search([
            *ResPartner._check_company_domain(company),
            ('parent_id', '=', False),
            ('routing_scheme', '=', routing_scheme),
            ('routing_endpoint', '=', routing_endpoint),
        ], limit=2)
        return partners if len(partners) == 1 else ResPartner

    def _import_partner(self, company_id, name, phone, email, vat, *, routing_scheme=None, routing_endpoint=None, **kwargs):
        """ EXTENDS `account.edi.common`: the partner is first matched on the EndpointID of the
        document, and an existing partner is never modified. A partner created from the document
        gets its address and that EndpointID as its Peppol ID, but not the email and phone of the
        buyer contact.
        """
        if partner := self._retrieve_partner_from_endpoint(company_id, routing_scheme, routing_endpoint):
            return partner, []
        ResPartner = self.env['res.partner'].sudo().with_context(active_test=False)
        last_partner_id = ResPartner.search([], order='id desc', limit=1).id
        partner, logs = super()._import_partner(company_id, name, phone, email, vat, **kwargs)
        if partner.id > last_partner_id:
            partner.write({'email': False, 'phone': False})
            super()._import_partner_postal_address(partner, kwargs.get('postal_address', {}))
            if routing_endpoint and routing_scheme in ResPartner._fields['routing_scheme'].get_values(self.env):
                partner.write({'routing_scheme': routing_scheme, 'routing_endpoint': routing_endpoint})
        return partner, logs

    def _import_partner_postal_address(self, partner, postal_address):
        """ OVERRIDE of `account.edi.common`: an existing partner keeps its address, see
        `_import_partner`.
        """

    def _log_buyer_address_mismatch(self, order, buyer, tree):
        """ Log in the chatter of `order` where the address of the buyer in the document differs from
        the address of `buyer`, which is kept.
        """
        document_address = self._get_postal_address(tree, 'BuyerCustomer')
        commercial_partner = buyer.commercial_partner_id
        buyer_address = {
            'street': commercial_partner.street,
            'additional_street': commercial_partner.street2,
            'city': commercial_partner.city,
            'zip': commercial_partner.zip,
            'state_code': commercial_partner.state_id.code,
            'country_code': commercial_partner.country_id.code,
        }
        labels = {
            'street': self.env._("Street"),
            'additional_street': self.env._("Street 2"),
            'city': self.env._("City"),
            'zip': self.env._("ZIP"),
            'state_code': self.env._("State"),
            'country_code': self.env._("Country"),
        }
        mismatches = [
            self.env._("%(field)s: %(document)s (customer: %(customer)s)",
                field=label, document=document_address[key], customer=buyer_address[key] or '-')
            for key, label in labels.items()
            if document_address.get(key)
            and normalize_text(document_address[key]) != normalize_text(buyer_address[key])
        ]
        if mismatches:
            order._message_log(body=Markup("<b>%s</b><ul>%s</ul>") % (
                self.env._("The address of the buyer in the document differs from the address of %s, which is kept:", commercial_partner.display_name),
                Markup().join(Markup("<li>%s</li>") % mismatch for mismatch in mismatches),
            ))

    def _import_buyer_contact(self, order, buyer, tree):
        """ Return the customer of `order` for the contact of the buyer in the document. The contact
        is matched on its email only, and existing contacts are never modified. Whatever cannot be
        matched is logged in the chatter of `order`.
        """
        contact_node = tree.find('./{*}BuyerCustomerParty/{*}Party/{*}Contact')
        if contact_node is None:
            return buyer
        name = contact_node.findtext('./{*}Name')
        phone = contact_node.findtext('./{*}Telephone')
        email = contact_node.findtext('./{*}ElectronicMail')
        if not (name or phone or email):
            return buyer

        details = Markup().join(Markup("<li>%s</li>") % detail for detail in [
            name and self.env._("Name: %s", name),
            phone and self.env._("Phone: %s", phone),
            email and self.env._("Email: %s", email),
        ] if detail)

        def log(message):
            order._message_log(body=Markup("<b>%s</b><ul>%s</ul>") % (message, details))

        commercial_partner = buyer.commercial_partner_id
        if not commercial_partner.is_company:
            if (
                (name and name != commercial_partner.name)
                or (phone and phone != commercial_partner.phone)
                or (email and email.casefold() != (commercial_partner.email or '').casefold())
            ):
                log(self.env._("The buyer contact in the document differs from the customer, which is kept:"))
            return commercial_partner

        if not email:
            log(self.env._("The buyer contact in the document has no email to find it among the contacts of %s:", commercial_partner.display_name))
            return commercial_partner

        contacts = self.env['res.partner'].search([
            ('id', 'child_of', commercial_partner.id),
            ('email', '=ilike', escape_like_value(email)),
        ], limit=2)
        if len(contacts) == 1:
            return contacts
        if contacts:
            log(self.env._("Several contacts of %s have the email of the buyer contact in the document:", commercial_partner.display_name))
            return commercial_partner

        contact = self.env['res.partner'].create({
            'name': name or email,
            'phone': phone,
            'email': email,
            'parent_id': commercial_partner.id,
            'type': 'contact',
        })
        log(self.env._("Created the contact %(contact)s under %(company)s from the buyer contact in the document:",
            contact=contact.name, company=commercial_partner.display_name))
        return contact

    def _retrieve_order_vals(self, order, tree):
        """ OVERRIDE of `sale_edi_ubl.sale.edi.xml.ubl_bis3` to retrieve advanced order values
            from incoming order documents
        """
        order_vals, logs = super()._retrieve_order_vals(order, tree)

        # The quotation date is the creation date of the quotation, then its confirmation date, not
        # a date from the document (the parent takes cbc:EndDate or cbc:IssueDate).
        order_vals.pop('date_order', None)

        # The parent module `sale_edi_ubl` imports the document ID as client_order_ref field. The SG
        # government requirement specifies the customer reference value (cbc:CustomerReference) to
        # be available on the SO. Also the customer reference value should be persisted when the SO
        # is flipped to invoice, which makes client_order_ref field ideal for storing this value.
        document_id = tree.findtext('./{*}ID')
        order_vals['l10n_sg_peppol_order_id'] = document_id
        endpoint_node = tree.find('./{*}BuyerCustomerParty/{*}Party/{*}EndpointID')
        if endpoint_node is not None and endpoint_node.get('schemeID') and endpoint_node.text:
            order_vals['l10n_sg_peppol_buyer_endpoint'] = f"{endpoint_node.get('schemeID')}:{endpoint_node.text}"
        order_vals['client_order_ref'] = tree.findtext('./{*}CustomerReference')
        note_prefix = f'[{document_id}] ' if document_id else ''

        if partner_id := order_vals.get('partner_id'):
            buyer = self.env['res.partner'].browse(partner_id)
            self._log_buyer_address_mismatch(order, buyer, tree)
            order_vals['partner_id'] = self._import_buyer_contact(order, buyer, tree).id

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

        # The line note (cbc:Note) is a sibling of cac:LineItem, hence not parsed with the line values.
        for order_line_node in tree.findall('./{*}OrderLine'):
            line_id = order_line_node.findtext('./{*}LineItem/{*}ID')
            for line_cmd in order_vals.get('order_line', []):
                if line_cmd[2].get('l10n_sg_ubl_line_item_ref') == line_id:
                    line_cmd[2]['l10n_sg_line_note'] = order_line_node.findtext('./{*}Note') or False
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

        period_node = tree.find('./{*}Delivery/{*}RequestedDeliveryPeriod')
        if period_node is not None:
            # A time without a UTC offset (e.g. '09:00:00') is assumed to be in the timezone of the
            # company receiving the order.
            tz = ZoneInfo(record.company_id.partner_id.tz or 'UTC')
            line_vals.update({
                'l10n_sg_delivery_start': self._parse_ubl_datetime(
                    period_node.findtext('./{*}StartDate'), period_node.findtext('./{*}StartTime'), tz,
                ),
                'l10n_sg_delivery_end': self._parse_ubl_datetime(
                    period_node.findtext('./{*}EndDate'), period_node.findtext('./{*}EndTime'), tz, end_of_day=True,
                ),
            })
        return line_vals

    def _import_order_delivery_partner(self, order, tree):
        """ OVERRIDE of `sale_edi_ubl.sale.edi.xml.ubl_bis3`: the delivery information is matched
        against the buyer and its contacts rather than all partners, and becomes a new delivery
        address of the buyer when nothing matches. Without delivery information, the order is
        delivered to the buyer.
        """
        buyer = order.partner_id
        delivery_vals = self._import_retrieve_delivery_vals(tree)
        if not buyer or not delivery_vals:
            return buyer, []

        commercial_partner = buyer.commercial_partner_id
        candidates = buyer | self.env['res.partner'].search(
            [('id', 'child_of', commercial_partner.id)],
        ).sorted(lambda partner: partner.type != 'delivery')

        if gln := delivery_vals.get('global_location_number'):
            partner = (
                candidates.filtered(lambda partner: partner.global_location_number == gln)[:1]
                or self.env['res.partner']._retrieve_partner(
                    additional_identifiers={'EAN_GLN': gln}, company=order.company_id,
                )
            )
            if partner:
                return partner, []

        has_address = 'country_id' in delivery_vals
        if has_address:
            address_fields = ['street', 'street2', 'city', 'zip', 'state_id', 'country_id']
            delivery_address = [normalize_text(delivery_vals.get(field)) for field in address_fields]
            candidates = candidates.filtered(lambda partner: delivery_address == [
                normalize_text(value)
                for value in partner._convert_to_write({field: partner[field] for field in address_fields}).values()
            ])
        if name := normalize_text(delivery_vals.get('name')):
            partner = candidates.filtered(lambda partner: normalize_text(partner.name) == name)[:1]
            if partner:
                return partner, []
        if has_address and candidates:
            return candidates[0], []

        partner = self.env['res.partner'].create({
            **delivery_vals,
            'parent_id': commercial_partner.id,
            'type': 'delivery',
        })
        order._message_log(body=Markup("<b>%s</b>") % self.env._(
            "Created new delivery address '%(address)s' under '%(company_name)s' from the order's delivery information.",
            address=partner.display_name, company_name=commercial_partner.display_name,
        ))
        return partner, []

    def _import_retrieve_delivery_vals(self, tree):
        """ Read the order's delivery location and party as `res.partner` values. The address and GLN
        are read from the delivery location first, then from the delivery party.
        :return: the partner values, empty when the order has no delivery information.
        """
        delivery_node = tree.find('./{*}Delivery')
        if delivery_node is None:
            return {}

        ResPartner = self.env['res.partner']
        gln = (
            delivery_node.findtext("./{*}DeliveryLocation/{*}ID[@schemeID='0088']")
            or delivery_node.findtext("./{*}DeliveryParty/{*}PartyIdentification/{*}ID[@schemeID='0088']")
        )
        gln_validation = ResPartner._validate_identifier('EAN_GLN', gln)
        vals = {
            'name': (
                delivery_node.findtext('./{*}DeliveryParty/{*}PartyName/{*}Name')
                or delivery_node.findtext('./{*}DeliveryLocation/{*}Name')
            ),
            'phone': delivery_node.findtext('./{*}DeliveryParty/{*}Contact/{*}Telephone'),
            'email': delivery_node.findtext('./{*}DeliveryParty/{*}Contact/{*}ElectronicMail'),
            'global_location_number': gln_validation['value'] if gln_validation['valid'] else None,
        }

        address_node = delivery_node.find('./{*}DeliveryLocation/{*}Address')
        if address_node is None:
            address_node = delivery_node.find('./{*}DeliveryParty/{*}PostalAddress')
        country_code = address_node is not None and address_node.findtext('./{*}Country/{*}IdentificationCode')
        if country := country_code and self.env['res.country'].search([('code', '=', country_code.strip().upper())], limit=1):
            subentity = (address_node.findtext('./{*}CountrySubentity') or '').strip()
            vals.update({
                'street': address_node.findtext('./{*}StreetName'),
                'street2': address_node.findtext('./{*}AdditionalStreetName'),
                'city': address_node.findtext('./{*}CityName'),
                'zip': address_node.findtext('./{*}PostalZone'),
                'country_id': country.id,
                'state_id': subentity and self.env['res.country.state'].search([
                    ('country_id', '=', country.id),
                    '|', ('code', '=', subentity), ('name', '=ilike', subentity),
                ], limit=1).id,
            })
        return {field: value for field, value in vals.items() if value}

    def log_buyer_mismatch(self, order, tree):
        """ Log in the chatter of `order` where the buyer of a document received for it differs from
        the order's customer. The customer is kept as is.
        """
        partner_vals = self._import_retrieve_partner_vals(tree, 'BuyerCustomer')
        buyer = self._retrieve_partner_from_endpoint(
            order.company_id, partner_vals.get('routing_scheme'), partner_vals.get('routing_endpoint'),
        ) or self.env['res.partner'].with_company(order.company_id)._retrieve_partner(
            name=partner_vals['name'],
            phone=partner_vals['phone'],
            email=partner_vals['email'],
            vat=partner_vals['vat'],
            additional_identifiers=partner_vals.get('additional_identifiers'),
        )
        customer = order.partner_id
        mismatches = []
        if buyer.commercial_partner_id != customer.commercial_partner_id:
            mismatches.append(self.env._(
                "Buyer: %(document)s (order: %(order)s)",
                document=buyer.commercial_partner_id.display_name or partner_vals['name'] or '-',
                order=customer.commercial_partner_id.display_name,
            ))
        contact_name = tree.findtext('./{*}BuyerCustomerParty/{*}Party/{*}Contact/{*}Name')
        contact_email = tree.findtext('./{*}BuyerCustomerParty/{*}Party/{*}Contact/{*}ElectronicMail')
        if contact_email and contact_email.casefold() != (customer.email or '').casefold():
            if contact_name and contact_name != customer.name:
                mismatches.append(self.env._(
                    "Contact name: %(document)s (order: %(order)s)", document=contact_name, order=customer.name or '-',
                ))
            mismatches.append(self.env._(
                "Contact email: %(document)s (order: %(order)s)", document=contact_email, order=customer.email or '-',
            ))
        if mismatches:
            order.message_post(body=Markup("<b>%s</b><ul>%s</ul>") % (
                self.env._("The buyer in the document differs from the order's customer, which is kept:"),
                Markup().join(Markup("<li>%s</li>") % mismatch for mismatch in mismatches),
            ))

    def _parse_ubl_datetime(self, date_str, time_str, tz, end_of_day=False):
        """Combine UBL cbc:*Date and cbc:*Time values into a naive UTC datetime, as stored by Odoo.

        :param tz: timezone of the time when it has no offset
        :param end_of_day: when there is no time, use the end of the day instead of its start
        """
        if not date_str:
            return False
        time_str = time_str or ('23:59:59' if end_of_day else '00:00:00')
        try:
            value = datetime.fromisoformat(f'{date_str.strip()}T{time_str.strip()}')
        except ValueError:
            return False
        if value.tzinfo is None:
            value = value.replace(tzinfo=tz)
        return value.astimezone(UTC).replace(tzinfo=None)

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

    def _import_partner(self, company_id, *args, **kwargs):
        """ OVERRIDE of `account.edi.common`: an order change applies to an existing order, whose
        customer is never re-resolved.
        """
        return self.env['res.partner'], []

    def _import_order_delivery_partner(self, order, tree):
        """ OVERRIDE of `sale.edi.xml.ubl_bis3_advanced_order`: the delivery address of an order
        change is resolved only when the change is applied, see `process_peppol_order_change`.
        """
        return self.env['res.partner'], []

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
        currency_code = tree.findtext('./{*}DocumentCurrencyCode')
        if currency_code and currency_code != order.currency_id.name:
            html_output += Markup("<li><b>%s</b></li>") % self.env._(
                "The currency of the order change, %(document)s, differs from the order's, %(order)s: its"
                " amounts are applied as %(order)s amounts, without conversion.",
                document=currency_code, order=order.currency_id.name,
            )
        for line_tree in tree.iterfind('./{*}OrderLine/{*}LineItem'):
            line_vals = self._retrieve_line_vals(order, line_tree)
            line_status_code = line_vals.pop('line_status_code')
            tax_ids, _tax_logs = self._retrieve_taxes(order, line_vals, 'sale')
            taxes = self.env['account.tax'].browse(tax_ids)
            if line_status_code == '1':
                product = self.env['product.product'].browse(line_vals.get('product_id'))
                html_output += Markup("<li>Line added: %s</li>") % (product.display_name or line_vals.get('name'))
                html_output += Markup("<ul>")
                html_output += Markup("<li>Quantity: %s</li>") % line_vals['product_uom_qty']
                html_output += Markup("<li>Unit Price: %s</li>") % line_vals['price_unit']
                if line_vals['discount'] != 0:
                    html_output += Markup("<li>Discount %s</li>") % line_vals['discount']
                if taxes:
                    html_output += Markup("<li>Taxes: %s</li>") % ", ".join(taxes.mapped('display_name'))
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
                html_output += Markup("<li>Line deleted: %s</li>") % (line.product_id.display_name or line.name)
            elif line_status_code == '3':  # Order line is changed
                currency = order.currency_id

                html_output += Markup("<li>Line changed: %s</li>") % (line.product_id.display_name or line.name)
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
                if line.tax_ids != taxes:
                    html_output += Markup("<li>Taxes: %s -> %s</li>") % (
                        ", ".join(line.tax_ids.mapped('display_name')) or '-',
                        ", ".join(taxes.mapped('display_name')) or '-',
                    )
                for field_name in ('l10n_sg_delivery_start', 'l10n_sg_delivery_end'):
                    if field_name in line_vals and line[field_name] != (line_vals[field_name] or False):
                        field = line._fields[field_name]
                        html_output += Markup("<li>%s: %s -> %s</li>") % (
                            field._description_string(self.env),
                            field.convert_to_display_name(line[field_name], line) or '-',
                            field.convert_to_display_name(line_vals[field_name], line) or '-',
                        )

                html_output += Markup("</ul>")

        html_output += self._get_order_change_delivery_diff(order, tree)
        html_output += Markup("</ul>")
        order.message_post(body=html_output)

    def _get_order_change_delivery_diff(self, order, tree):
        """ Return the changes the delivery information of the order change brings to the delivery
        address of `order`, as an HTML list item.
        """
        delivery_vals = self._import_retrieve_delivery_vals(tree)
        if not delivery_vals:
            return Markup()
        shipping_partner = order.partner_shipping_id
        new_partner = self.env['res.partner'].new(delivery_vals)
        changes = Markup()
        for field_name in delivery_vals:
            field = shipping_partner._fields[field_name]
            old_value = field.convert_to_display_name(shipping_partner[field_name], shipping_partner)
            new_value = field.convert_to_display_name(new_partner[field_name], new_partner)
            if normalize_text(old_value) != normalize_text(new_value):
                changes += Markup("<li>%s: %s -> %s</li>") % (field._description_string(self.env), old_value or '-', new_value)
        if not changes:
            return Markup()
        return Markup("<li>%s</li><ul>%s</ul>") % (
            self.env._("Delivery address changed: %s", shipping_partner.display_name), changes,
        )

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

        if self._import_retrieve_delivery_vals(tree):
            delivery_partner, delivery_logs = super()._import_order_delivery_partner(order, tree)
            order.partner_shipping_id = delivery_partner
            logs += delivery_logs

        doc_id = order_vals.get('l10n_sg_peppol_order_id')
        body = self.env._("Applied InvoiceNow (Peppol) order change document")
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

    def process_peppol_order_cancel(self, order, attachment):
        """
        Apply PEPPOL order cancellation document to `sale_order`. Searches through the sale order's
        PEPPOL transactions and apply the most recent order cancellation request to the order.
        """
        # Call cancellation first to check for any UserError
        order.action_cancel()

        tree = self.env['account.move']._to_files_data(attachment)[0]['xml_tree']
        if cancellation_note := tree.findtext('./{*}CancellationNote'):
            msg = self.env._("Applied InvoiceNow (Peppol) order cancellation document: %s", cancellation_note)
        else:
            msg = self.env._("Applied InvoiceNow (Peppol) order cancellation document")

        if doc_id := tree.findtext('./{*}ID'):
            msg = Markup("%s (ID: %s)") % (msg, escape(doc_id))
        order.message_post(body=msg)
        order.message_post(body=Markup("<strong>%s</strong>") % self.env._("Format used to import the document: %s", self._description))


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
        OVERRIDE of `account.edi.ubl`. The buyer customer party should not have 'cac:PartyTaxScheme',
        and its EndpointID is the one the order was received from.
        """
        node = vals['document_node']['cac:BuyerCustomerParty'] = {'cac:Party': {}}
        party_node = node['cac:Party']
        sub_vals = {
            **vals,
            'party_vals': {'partner': vals['customer']},
            'party_node': party_node,
        }
        self._ubl_add_accounting_supplier_party_endpoint_id_node(sub_vals)
        if buyer_endpoint := vals['sale_order'].l10n_sg_peppol_buyer_endpoint:
            scheme, _sep, endpoint = buyer_endpoint.partition(':')
            party_node['cbc:EndpointID'] = {'_text': endpoint, 'schemeID': scheme}
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
            tz = ZoneInfo(sale_order.company_id.partner_id.tz or 'UTC')
            commitment_date = sale_order.commitment_date.replace(tzinfo=UTC).astimezone(tz)
            date_str = commitment_date.strftime("%Y-%m-%d")
            time_str = commitment_date.strftime("%H:%M:%S")

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

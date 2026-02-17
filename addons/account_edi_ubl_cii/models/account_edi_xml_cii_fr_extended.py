from lxml import etree
from odoo import models

# CII Namespaces
CII_NAMESPACES = {
    'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    'rsm': "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    'qdt': "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}

NSMAP = {
    'ram': CII_NAMESPACES['ram'],
    'udt': CII_NAMESPACES['udt'],
    'qdt': CII_NAMESPACES['qdt'],
}


def _make_elem(tag, text=None, attrib=None):
    """Helper to create an lxml element with proper namespace handling."""
    if ':' in tag:
        prefix, local = tag.split(':', 1)
        ns = NSMAP.get(prefix, CII_NAMESPACES.get(prefix))
        if ns:
            tag = '{%s}%s' % (ns, local)
    elem = etree.Element(tag, attrib=attrib or {})
    if text is not None:
        elem.text = str(text)
    return elem


class AccountEdiXmlCiiFrExtended(models.AbstractModel):
    _name = "account.edi.xml.cii_fr_extended"
    _inherit = "account.edi.xml.cii_fr"
    _description = "UN/CEFACT CII France CIUS Extended"

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cii_fr_extended.xml"

    def _get_document_context_id(self):
        """Return the document context ID for France CIUS Extended."""
        return "urn:cen.eu:en16931:2017#conformant#urn.cpro.gouv.fr:1p0:extended-ctc-fr"

    # -------------------------------------------------------------------------
    # EXPORT: Extended French values
    # -------------------------------------------------------------------------

    def _get_french_vals(self, invoice):
        """Get French values including Extended profile additions."""
        vals = super()._get_french_vals(invoice)

        # Add Extended-specific values
        vals.update({
            # Business Process (BT-23)
            'business_process': self._get_business_process(invoice),

            # Agent parties
            'sales_agent': self._get_agent_party_vals(invoice, 'sales_agent'),
            'buyer_agent': self._get_agent_party_vals(invoice, 'buyer_agent'),
            'invoicer': self._get_agent_party_vals(invoice, 'invoicer'),
            'invoicee': self._get_agent_party_vals(invoice, 'invoicee'),
            'payer': self._get_agent_party_vals(invoice, 'payer'),

            # Contract reference extension (BT-X-405)
            'contract_reference_type': self._get_contract_reference_type(invoice),

            # Invoice reference extension (BT-X-555)
            'invoice_reference_type': self._get_invoice_reference_type(invoice),

            # Extended line vals
            'extended_line_vals': self._get_extended_line_vals(invoice),
        })

        return vals

    def _get_business_process(self, invoice):
        """Get business process specification (BT-23)."""
        if 'l10n_fr_business_process_id' not in invoice._fields:
            return None
        return invoice.l10n_fr_business_process_id or None

    def _get_agent_party_vals(self, invoice, agent_type):
        """Get agent trade party values for a given agent type."""
        field_name = f'l10n_fr_{agent_type}_id'
        if field_name not in invoice._fields:
            return None
        agent = invoice[field_name]
        if not agent:
            return None

        return self._build_agent_party_vals(agent, agent_type)

    def _build_agent_party_vals(self, agent, agent_type):
        """Build the complete agent party values structure."""
        vals = {
            'id': agent.ref,
            'global_ids': self._get_partner_global_ids(agent),
            'name': agent.name,
            'role_code': self._get_agent_role_code(agent_type),
        }

        # Legal organization
        siret = (agent.siret or None) if 'siret' in agent._fields else None
        registry = (agent.company_registry or '').strip() if agent.company_registry else ''
        legal_id = None
        legal_scheme = None
        if siret:
            siret = siret.strip()
            if len(siret) == 14 and siret.isdigit():
                legal_id = siret
                legal_scheme = '0009'
            elif len(siret) == 9 and siret.isdigit():
                legal_id = siret
                legal_scheme = '0002'
        elif registry:
            if len(registry) == 14 and registry.isdigit():
                legal_id = registry
                legal_scheme = '0009'
            elif len(registry) == 9 and registry.isdigit():
                legal_id = registry
                legal_scheme = '0002'

        if legal_id:
            vals['legal_organization'] = {
                'id': legal_id,
                'scheme_id': legal_scheme,
                'trading_business_name': (
                    agent.l10n_fr_trading_name or None
                    if 'l10n_fr_trading_name' in agent._fields
                    else None
                ),
            }

        # Trade contacts
        vals['trade_contacts'] = self._get_agent_trade_contacts(agent)

        # Address info
        vals['street'] = agent.street
        vals['street2'] = agent.street2
        vals['street3'] = (agent.street3 or None) if 'street3' in agent._fields else None
        vals['zip'] = agent.zip
        vals['city'] = agent.city
        vals['country'] = agent.country_id.code if agent.country_id else None
        vals['country_subdivision_name'] = agent.state_id.name if agent.state_id else None

        # URI Communication
        if 'l10n_fr_uri_id' in agent._fields and agent.l10n_fr_uri_id:
            uri_scheme_id = (
                agent.l10n_fr_uri_scheme_id
                if 'l10n_fr_uri_scheme_id' in agent._fields
                else None
            )
            if uri_scheme_id:
                vals['uri_id'] = agent.l10n_fr_uri_id
                vals['uri_scheme_id'] = uri_scheme_id

        # Tax registration
        if agent.vat:
            vals['tax_registration'] = {
                'id': agent.vat,
                'scheme_id': 'VA',
            }

        return vals

    def _get_agent_role_code(self, agent_type):
        """Get the role code for an agent type."""
        role_codes = {
            'sales_agent': 'SA',
            'buyer_agent': 'BA',
            'invoicer': 'IV',
            'invoicee': 'IE',
            'payer': 'PY',
        }
        return role_codes.get(agent_type)

    def _get_agent_trade_contacts(self, agent):
        """Get trade contact information for an agent."""
        contacts = []
        if agent.phone or agent.mobile or agent.email:
            contacts.append({
                'person_name': agent.name,
                'department_name': (
                    agent.l10n_fr_department_name or None
                    if 'l10n_fr_department_name' in agent._fields
                    else None
                ),
                'telephone': agent.phone or agent.mobile,
                'email': agent.email,
            })
        return contacts

    def _get_contract_reference_type(self, invoice):
        """Get extended contract reference type code (BT-X-405)."""
        if 'l10n_fr_contract_reference_type' not in invoice._fields:
            return None
        return invoice.l10n_fr_contract_reference_type or None

    def _get_invoice_reference_type(self, invoice):
        """Get extended invoice reference type code (BT-X-555)."""
        if 'l10n_fr_invoice_reference_type' not in invoice._fields:
            return None
        return invoice.l10n_fr_invoice_reference_type or None

    def _get_extended_line_vals(self, invoice):
        """Get Extended line-specific values."""
        line_vals = {}

        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            vals = {}

            # BG-X-81: Seller Order Referenced Document
            if 'l10n_fr_seller_order_ref' in line._fields and line.l10n_fr_seller_order_ref:
                vals['seller_order_reference'] = {
                    'issuer_assigned_id': line.l10n_fr_seller_order_ref,
                    'line_id': (
                        line.l10n_fr_seller_order_line_id or None
                        if 'l10n_fr_seller_order_line_id' in line._fields
                        else None
                    ),
                }

            # BT-X-21: Buyer Order Issuer Assigned ID
            if 'l10n_fr_buyer_order_issuer_id' in line._fields and line.l10n_fr_buyer_order_issuer_id:
                vals['buyer_order_issuer_assigned_id'] = line.l10n_fr_buyer_order_issuer_id

            # BG-X-7: Ship To Trade Party at line level
            if 'l10n_fr_line_ship_to_id' in line._fields and line.l10n_fr_line_ship_to_id:
                ship_to = line.l10n_fr_line_ship_to_id
                vals['ship_to_trade_party'] = {
                    'id': ship_to.ref,
                    'global_ids': self._get_partner_global_ids(ship_to),
                    'name': ship_to.name,
                    'street': ship_to.street,
                    'street2': ship_to.street2,
                    'street3': (
                        (ship_to.street3 or None)
                        if 'street3' in ship_to._fields else None
                    ),
                    'zip': ship_to.zip,
                    'city': ship_to.city,
                    'country': ship_to.country_id.code if ship_to.country_id else None,
                    'country_subdivision_name': ship_to.state_id.name if ship_to.state_id else None,
                }

            # BT-X-85: Actual Delivery Date at line level
            if 'l10n_fr_line_delivery_date' in line._fields and line.l10n_fr_line_delivery_date:
                vals['actual_delivery_date'] = line.l10n_fr_line_delivery_date.strftime('%Y%m%d')

            # BG-X-13: Despatch Advice Referenced Document
            if 'l10n_fr_line_despatch_ref' in line._fields and line.l10n_fr_line_despatch_ref:
                vals['despatch_advice_reference'] = {
                    'issuer_assigned_id': line.l10n_fr_line_despatch_ref,
                    'line_id': (
                        line.l10n_fr_line_despatch_line_id or None
                        if 'l10n_fr_line_despatch_line_id' in line._fields
                        else None
                    ),
                }

            # BG-X-82: Receiving Advice Referenced Document
            if 'l10n_fr_line_receiving_ref' in line._fields and line.l10n_fr_line_receiving_ref:
                vals['receiving_advice_reference'] = {
                    'issuer_assigned_id': line.l10n_fr_line_receiving_ref,
                    'line_id': (
                        line.l10n_fr_line_receiving_line_id or None
                        if 'l10n_fr_line_receiving_line_id' in line._fields
                        else None
                    ),
                }

            # BG-X-48: Invoice Referenced Document at line level
            if 'l10n_fr_line_invoice_ref' in line._fields and line.l10n_fr_line_invoice_ref:
                vals['invoice_reference'] = {
                    'issuer_assigned_id': line.l10n_fr_line_invoice_ref,
                    'line_id': (
                        line.l10n_fr_line_invoice_line_id or None
                        if 'l10n_fr_line_invoice_line_id' in line._fields
                        else None
                    ),
                    'type_code': (
                        line.l10n_fr_line_invoice_type_code or None
                        if 'l10n_fr_line_invoice_type_code' in line._fields
                        else None
                    ),
                }
                if 'l10n_fr_line_invoice_date' in line._fields and line.l10n_fr_line_invoice_date:
                    vals['invoice_reference']['issue_date'] = line.l10n_fr_line_invoice_date.strftime('%Y%m%d')

            if vals:
                line_vals[line.id] = vals

        return line_vals

    # -------------------------------------------------------------------------
    # EXPORT: XML Modifications
    # -------------------------------------------------------------------------

    def _apply_french_modifications(self, tree, fr_vals, invoice):
        """Apply all French-specific modifications including Extended profile."""
        # Apply base France CIUS modifications
        super()._apply_french_modifications(tree, fr_vals, invoice)

        # Add Business Process
        if fr_vals.get('business_process'):
            self._add_business_process(tree, fr_vals['business_process'])

        # Add Agent Parties
        for agent_type in ['sales_agent', 'buyer_agent']:
            if fr_vals.get(agent_type):
                self._add_agent_party(tree, fr_vals[agent_type], agent_type, 'agreement')

        for agent_type in ['invoicer', 'invoicee', 'payer']:
            if fr_vals.get(agent_type):
                self._add_agent_party(tree, fr_vals[agent_type], agent_type, 'settlement')

        # Add Contract Reference Type Code
        if fr_vals.get('contract_reference_type'):
            self._add_contract_reference_type(tree, fr_vals['contract_reference_type'])

        # Add Invoice Reference Type Code
        if fr_vals.get('invoice_reference_type'):
            self._add_invoice_reference_type(tree, fr_vals['invoice_reference_type'])

        # Add Extended Line modifications
        if fr_vals.get('extended_line_vals'):
            self._modify_extended_lines(tree, fr_vals['extended_line_vals'], invoice)

    def _add_business_process(self, tree, process_id):
        """Add BusinessProcessSpecifiedDocumentContextParameter (BT-23)."""
        context = tree.find('.//rsm:ExchangedDocumentContext', CII_NAMESPACES)
        if context is None:
            return

        bp_param = _make_elem('ram:BusinessProcessSpecifiedDocumentContextParameter')
        bp_param.append(_make_elem('ram:ID', process_id))

        # Insert at beginning of context
        context.insert(0, bp_param)

    def _add_agent_party(self, tree, vals, agent_type, location):
        """Add an agent trade party element."""
        if location == 'agreement':
            parent = tree.find('.//ram:ApplicableHeaderTradeAgreement', CII_NAMESPACES)
        else:
            parent = tree.find('.//ram:ApplicableHeaderTradeSettlement', CII_NAMESPACES)

        if parent is None:
            return

        # Determine element name
        element_names = {
            'sales_agent': 'ram:SalesAgentTradeParty',
            'buyer_agent': 'ram:BuyerAgentTradeParty',
            'invoicer': 'ram:InvoicerTradeParty',
            'invoicee': 'ram:InvoiceeTradeParty',
            'payer': 'ram:PayerTradeParty',
        }
        elem_name = element_names.get(agent_type)
        if not elem_name:
            return

        agent_elem = _make_elem(elem_name)

        # ID
        if vals.get('id'):
            agent_elem.append(_make_elem('ram:ID', vals['id']))

        # Global IDs
        for gid in vals.get('global_ids', []):
            global_id = _make_elem('ram:GlobalID', gid.get('id'))
            if gid.get('scheme_id'):
                global_id.set('schemeID', gid['scheme_id'])
            agent_elem.append(global_id)

        # Name
        if vals.get('name'):
            agent_elem.append(_make_elem('ram:Name', vals['name']))

        # Role Code
        if vals.get('role_code'):
            agent_elem.append(_make_elem('ram:RoleCode', vals['role_code']))

        # Legal Organization
        if vals.get('legal_organization'):
            legal_org = vals['legal_organization']
            org_elem = _make_elem('ram:SpecifiedLegalOrganization')
            org_id = _make_elem('ram:ID', legal_org.get('id'))
            if legal_org.get('scheme_id'):
                org_id.set('schemeID', legal_org['scheme_id'])
            org_elem.append(org_id)
            if legal_org.get('trading_business_name'):
                org_elem.append(_make_elem('ram:TradingBusinessName', legal_org['trading_business_name']))
            agent_elem.append(org_elem)

        # Trade Contacts
        for contact in vals.get('trade_contacts', []):
            contact_elem = _make_elem('ram:DefinedTradeContact')
            if contact.get('person_name'):
                contact_elem.append(_make_elem('ram:PersonName', contact['person_name']))
            if contact.get('department_name'):
                contact_elem.append(_make_elem('ram:DepartmentName', contact['department_name']))
            if contact.get('telephone'):
                tel = _make_elem('ram:TelephoneUniversalCommunication')
                tel.append(_make_elem('ram:CompleteNumber', contact['telephone']))
                contact_elem.append(tel)
            if contact.get('email'):
                email = _make_elem('ram:EmailURIUniversalCommunication')
                email.append(_make_elem('ram:URIID', contact['email']))
                contact_elem.append(email)
            agent_elem.append(contact_elem)

        # Address
        address = _make_elem('ram:PostalTradeAddress')
        if vals.get('zip'):
            address.append(_make_elem('ram:PostcodeCode', vals['zip']))
        if vals.get('street'):
            address.append(_make_elem('ram:LineOne', vals['street']))
        if vals.get('street2'):
            address.append(_make_elem('ram:LineTwo', vals['street2']))
        if vals.get('street3'):
            address.append(_make_elem('ram:LineThree', vals['street3']))
        if vals.get('city'):
            address.append(_make_elem('ram:CityName', vals['city']))
        if vals.get('country'):
            address.append(_make_elem('ram:CountryID', vals['country']))
        if vals.get('country_subdivision_name'):
            address.append(_make_elem('ram:CountrySubDivisionName', vals['country_subdivision_name']))
        agent_elem.append(address)

        # URI Communication
        if vals.get('uri_id'):
            uri = _make_elem('ram:URIUniversalCommunication')
            uri_id = _make_elem('ram:URIID', vals['uri_id'])
            if vals.get('uri_scheme_id'):
                uri_id.set('schemeID', vals['uri_scheme_id'])
            uri.append(uri_id)
            agent_elem.append(uri)

        # Tax Registration
        if vals.get('tax_registration'):
            tax_reg = _make_elem('ram:SpecifiedTaxRegistration')
            tax_id = _make_elem('ram:ID', vals['tax_registration']['id'])
            if vals['tax_registration'].get('scheme_id'):
                tax_id.set('schemeID', vals['tax_registration']['scheme_id'])
            tax_reg.append(tax_id)
            agent_elem.append(tax_reg)

        parent.append(agent_elem)

    def _add_contract_reference_type(self, tree, type_code):
        """Add ReferenceTypeCode to ContractReferencedDocument (BT-X-405)."""
        contract = tree.find('.//ram:ContractReferencedDocument', CII_NAMESPACES)
        if contract is not None:
            contract.append(_make_elem('ram:ReferenceTypeCode', type_code))

    def _add_invoice_reference_type(self, tree, type_code):
        """Add TypeCode to InvoiceReferencedDocument (BT-X-555)."""
        invoice_refs = tree.findall('.//ram:InvoiceReferencedDocument', CII_NAMESPACES)
        for ref in invoice_refs:
            ref.append(_make_elem('ram:TypeCode', type_code))

    def _modify_extended_lines(self, tree, line_vals_dict, invoice):
        """Apply Extended line-level modifications."""
        if not line_vals_dict:
            return

        lines = tree.findall('.//ram:IncludedSupplyChainTradeLineItem', CII_NAMESPACES)
        invoice_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')

        for idx, line_elem in enumerate(lines):
            if idx >= len(invoice_lines):
                continue

            invoice_line = invoice_lines[idx]
            vals = line_vals_dict.get(invoice_line.id, {})

            if not vals:
                continue

            # Seller Order Referenced Document
            if vals.get('seller_order_reference'):
                agreement = line_elem.find('ram:SpecifiedLineTradeAgreement', CII_NAMESPACES)
                if agreement is not None:
                    seller_order = _make_elem('ram:SellerOrderReferencedDocument')
                    seller_order.append(_make_elem('ram:IssuerAssignedID',
                                                   vals['seller_order_reference']['issuer_assigned_id']))
                    if vals['seller_order_reference'].get('line_id'):
                        seller_order.append(_make_elem('ram:LineID',
                                                       vals['seller_order_reference']['line_id']))
                    agreement.append(seller_order)

            # Buyer Order Issuer Assigned ID
            if vals.get('buyer_order_issuer_assigned_id'):
                buyer_order = line_elem.find('.//ram:BuyerOrderReferencedDocument', CII_NAMESPACES)
                if buyer_order is not None:
                    buyer_order.append(_make_elem('ram:IssuerAssignedID',
                                                  vals['buyer_order_issuer_assigned_id']))

            # Ship To Trade Party at line level
            if vals.get('ship_to_trade_party'):
                delivery = line_elem.find('ram:SpecifiedLineTradeDelivery', CII_NAMESPACES)
                if delivery is not None:
                    ship_to = vals['ship_to_trade_party']
                    ship_to_elem = _make_elem('ram:ShipToTradeParty')

                    if ship_to.get('id'):
                        ship_to_elem.append(_make_elem('ram:ID', ship_to['id']))
                    for gid in ship_to.get('global_ids', []):
                        global_id = _make_elem('ram:GlobalID', gid.get('id'))
                        if gid.get('scheme_id'):
                            global_id.set('schemeID', gid['scheme_id'])
                        ship_to_elem.append(global_id)
                    if ship_to.get('name'):
                        ship_to_elem.append(_make_elem('ram:Name', ship_to['name']))

                    address = _make_elem('ram:PostalTradeAddress')
                    if ship_to.get('zip'):
                        address.append(_make_elem('ram:PostcodeCode', ship_to['zip']))
                    if ship_to.get('street'):
                        address.append(_make_elem('ram:LineOne', ship_to['street']))
                    if ship_to.get('street2'):
                        address.append(_make_elem('ram:LineTwo', ship_to['street2']))
                    if ship_to.get('street3'):
                        address.append(_make_elem('ram:LineThree', ship_to['street3']))
                    if ship_to.get('city'):
                        address.append(_make_elem('ram:CityName', ship_to['city']))
                    if ship_to.get('country'):
                        address.append(_make_elem('ram:CountryID', ship_to['country']))
                    if ship_to.get('country_subdivision_name'):
                        address.append(_make_elem('ram:CountrySubDivisionName',
                                                  ship_to['country_subdivision_name']))
                    ship_to_elem.append(address)
                    delivery.append(ship_to_elem)

            # Actual Delivery Date at line level
            if vals.get('actual_delivery_date'):
                delivery = line_elem.find('ram:SpecifiedLineTradeDelivery', CII_NAMESPACES)
                if delivery is not None:
                    event = _make_elem('ram:ActualDeliverySupplyChainEvent')
                    occurrence = _make_elem('ram:OccurrenceDateTime')
                    date_str = _make_elem('udt:DateTimeString', vals['actual_delivery_date'])
                    date_str.set('format', '102')
                    occurrence.append(date_str)
                    event.append(occurrence)
                    delivery.append(event)

            # Despatch Advice Referenced Document at line level
            if vals.get('despatch_advice_reference'):
                delivery = line_elem.find('ram:SpecifiedLineTradeDelivery', CII_NAMESPACES)
                if delivery is not None:
                    despatch = _make_elem('ram:DespatchAdviceReferencedDocument')
                    despatch.append(_make_elem('ram:IssuerAssignedID',
                                               vals['despatch_advice_reference']['issuer_assigned_id']))
                    if vals['despatch_advice_reference'].get('line_id'):
                        despatch.append(_make_elem('ram:LineID',
                                                   vals['despatch_advice_reference']['line_id']))
                    delivery.append(despatch)

            # Receiving Advice Referenced Document at line level
            if vals.get('receiving_advice_reference'):
                delivery = line_elem.find('ram:SpecifiedLineTradeDelivery', CII_NAMESPACES)
                if delivery is not None:
                    receiving = _make_elem('ram:ReceivingAdviceReferencedDocument')
                    receiving.append(_make_elem('ram:IssuerAssignedID',
                                                vals['receiving_advice_reference']['issuer_assigned_id']))
                    if vals['receiving_advice_reference'].get('line_id'):
                        receiving.append(_make_elem('ram:LineID',
                                                    vals['receiving_advice_reference']['line_id']))
                    delivery.append(receiving)

            # Invoice Referenced Document at line level
            if vals.get('invoice_reference'):
                settlement = line_elem.find('ram:SpecifiedLineTradeSettlement', CII_NAMESPACES)
                if settlement is not None:
                    inv_ref = vals['invoice_reference']
                    ref_elem = _make_elem('ram:InvoiceReferencedDocument')
                    ref_elem.append(_make_elem('ram:IssuerAssignedID', inv_ref['issuer_assigned_id']))
                    if inv_ref.get('line_id'):
                        ref_elem.append(_make_elem('ram:LineID', inv_ref['line_id']))
                    if inv_ref.get('type_code'):
                        ref_elem.append(_make_elem('ram:TypeCode', inv_ref['type_code']))
                    if inv_ref.get('issue_date'):
                        issue_dt = _make_elem('ram:FormattedIssueDateTime')
                        date_str = _make_elem('qdt:DateTimeString', inv_ref['issue_date'])
                        date_str.set('format', '102')
                        issue_dt.append(date_str)
                        ref_elem.append(issue_dt)
                    settlement.append(ref_elem)

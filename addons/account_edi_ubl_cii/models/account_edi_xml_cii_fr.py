import re
from lxml import etree
from odoo import _, models
from odoo.tools import cleanup_xml_node

# CII Namespaces
CII_NAMESPACES = {
    'ram': "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    'rsm': "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    'udt': "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
    'qdt': "urn:un:unece:uncefact:data:standard:QualifiedDataType:100",
}

# Namespace map for element creation
NSMAP = {
    'ram': CII_NAMESPACES['ram'],
    'udt': CII_NAMESPACES['udt'],
    'qdt': CII_NAMESPACES['qdt'],
}


def _make_elem(tag, text=None, attrib=None, nsmap=None):
    """Helper to create an lxml element with proper namespace handling."""
    if ':' in tag:
        prefix, local = tag.split(':', 1)
        ns = NSMAP.get(prefix, CII_NAMESPACES.get(prefix))
        if ns:
            tag = '{%s}%s' % (ns, local)
    elem = etree.Element(tag, attrib=attrib or {}, nsmap=nsmap)
    if text is not None:
        elem.text = str(text)
    return elem


class AccountEdiXmlCiiFr(models.AbstractModel):
    _name = "account.edi.xml.cii_fr"
    _inherit = "account.edi.xml.cii"
    _description = "UN/CEFACT CII France CIUS EN16931"

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_cii_fr.xml"

    def _get_document_context_id(self):
        """Return the document context ID for France CIUS."""
        return "urn:cen.eu:en16931:2017"

    # -------------------------------------------------------------------------
    # EXPORT: Main export method
    # -------------------------------------------------------------------------

    def _export_invoice(self, invoice):
        """Export invoice to CII France CIUS format."""
        # Get base XML from parent
        xml_content, errors = super()._export_invoice(invoice)
        errors = set(errors)

        # French e-invoicing requires explicit electronic addresses for seller/buyer.
        errors.update(self._check_mandatory_electronic_addresses(invoice))

        # Parse the XML
        tree = etree.fromstring(xml_content)

        # Get French-specific values
        fr_vals = self._get_french_vals(invoice)

        # Apply French modifications
        self._apply_french_modifications(tree, fr_vals, invoice)

        # Update document context ID
        self._update_document_context(tree)

        return etree.tostring(cleanup_xml_node(tree), xml_declaration=True, encoding='UTF-8'), errors

    # -------------------------------------------------------------------------
    # EXPORT: French values preparation
    # -------------------------------------------------------------------------

    def _get_french_vals(self, invoice):
        """Prepare French-specific values for the invoice."""
        company = invoice.company_id
        partner = invoice.commercial_partner_id

        return {
            # Notes with subject codes (BT-21)
            'fr_notes': self._get_french_notes(invoice),

            # Seller party additions
            'seller_vals': self._get_party_french_vals(company.partner_id),

            # Buyer party additions
            'buyer_vals': self._get_party_french_vals(partner),

            # Ship-to party additions
            'ship_to_vals': self._get_party_french_vals(
                invoice.partner_shipping_id or partner
            ),

            # Tax representative (BG-11)
            'tax_representative_vals': self._get_tax_representative_vals(invoice),

            # Payee party (BG-10)
            'payee_vals': self._get_payee_vals(invoice),

            # Additional documents (BG-24)
            'additional_documents': self._get_additional_documents(invoice),

            # Seller order reference (BT-14)
            'seller_order_reference': self._get_seller_order_reference(invoice),

            # Despatch advice reference (BT-16)
            'despatch_advice_reference': self._get_despatch_advice_reference(invoice),

            # Receiving advice reference (BT-15)
            'receiving_advice_reference': self._get_receiving_advice_reference(invoice),

            # Procuring project (BT-11)
            'procuring_project': self._get_procuring_project(invoice),

            # Invoice line additions
            'line_vals': self._get_line_french_vals(invoice),
        }

    def _get_french_notes(self, invoice):
        """Get French-specific notes with subject codes."""
        notes = []

        # Mapping of field names to subject codes
        note_fields = {
            'l10n_fr_note_aab': 'AAB',  # Cash discount terms
            'l10n_fr_note_aai': 'AAI',  # General information
            'l10n_fr_note_abl': 'ABL',  # Legal information
            'l10n_fr_note_acc': 'ACC',  # Terms of sale
            'l10n_fr_note_blu': 'BLU',  # Eco-participation / DEEE
            'l10n_fr_note_dcl': 'DCL',  # Declaration
            'l10n_fr_note_pmt': 'PMT',  # Payment information
            'l10n_fr_note_pmd': 'PMD',  # Payment mode
            'l10n_fr_note_sur': 'SUR',  # Surcharges
            'l10n_fr_note_txd': 'TXD',  # Tax declaration (Single taxable person)
        }

        for field, subject_code in note_fields.items():
            if field not in invoice._fields:
                continue
            content = invoice[field]
            if content:
                notes.append({
                    'subject_code': subject_code,
                    'content': content,
                })

        return notes

    def _get_party_french_vals(self, partner):
        """Get French-specific values for a trade party."""
        if not partner:
            return {}

        vals = {}

        # Street3 / LineThree (BT-162/163/164/165)
        if 'street3' in partner._fields and partner.street3:
            vals['street3'] = partner.street3

        # Country Subdivision Name (BT-39/54/68/79)
        if partner.state_id:
            vals['country_subdivision_name'] = partner.state_id.name

        # Trading Business Name (BT-28/45)
        if 'l10n_fr_trading_name' in partner._fields and partner.l10n_fr_trading_name:
            vals['trading_business_name'] = partner.l10n_fr_trading_name

        # Description / Legal Form (BT-33)
        if 'l10n_fr_legal_form' in partner._fields and partner.l10n_fr_legal_form:
            vals['description'] = partner.l10n_fr_legal_form

        # Department Name (BT-41-0/56-0)
        if 'l10n_fr_department_name' in partner._fields and partner.l10n_fr_department_name:
            vals['department_name'] = partner.l10n_fr_department_name

        # URI Communication (BT-34/49)
        if 'l10n_fr_uri_id' in partner._fields and partner.l10n_fr_uri_id:
            vals['uri_id'] = partner.l10n_fr_uri_id
            if 'l10n_fr_uri_scheme_id' in partner._fields and partner.l10n_fr_uri_scheme_id:
                vals['uri_scheme_id'] = partner.l10n_fr_uri_scheme_id

        # Global IDs
        vals['global_ids'] = self._get_partner_global_ids(partner)

        return vals

    def _get_partner_global_ids(self, partner):
        """Get global identifiers for a partner."""
        global_ids = []

        # SIRET
        if 'siret' in partner._fields and partner.siret:
            global_ids.append({'id': partner.siret, 'scheme_id': '0002'})
        elif partner.company_registry:
            global_ids.append({'id': partner.company_registry, 'scheme_id': '0002'})

        # French-specific global ID
        if 'l10n_fr_global_id' in partner._fields and partner.l10n_fr_global_id:
            scheme_id = '0002'
            if 'l10n_fr_global_id_scheme' in partner._fields and partner.l10n_fr_global_id_scheme:
                scheme_id = partner.l10n_fr_global_id_scheme
            global_ids.append({
                'id': partner.l10n_fr_global_id,
                'scheme_id': scheme_id,
            })

        return global_ids

    def _get_tax_representative_vals(self, invoice):
        """Get tax representative party values (BG-11)."""
        if 'l10n_fr_tax_representative_id' not in invoice._fields:
            return None

        representative = invoice.l10n_fr_tax_representative_id
        if not representative:
            return None

        street3 = None
        if 'street3' in representative._fields and representative.street3:
            street3 = representative.street3

        return {
            'name': representative.name,
            'vat': representative.vat,
            'street': representative.street,
            'street2': representative.street2,
            'street3': street3,
            'zip': representative.zip,
            'city': representative.city,
            'country': representative.country_id.code if representative.country_id else None,
            'country_subdivision_name': representative.state_id.name if representative.state_id else None,
        }

    def _get_payee_vals(self, invoice):
        """Get payee trade party values (BG-10)."""
        if 'l10n_fr_payee_id' not in invoice._fields:
            return None

        payee = invoice.l10n_fr_payee_id
        if not payee:
            return None

        payee_siret = None
        if 'siret' in payee._fields and payee.siret:
            payee_siret = payee.siret

        return {
            'id': payee.ref,
            'global_ids': self._get_partner_global_ids(payee),
            'name': payee.name,
            'legal_org_id': payee.company_registry or payee_siret,
            'legal_org_scheme': '0002',
        }

    def _get_additional_documents(self, invoice):
        """Get additional referenced documents (BG-24)."""
        documents = []

        # Project reference
        if 'l10n_fr_project_reference' in invoice._fields and invoice.l10n_fr_project_reference:
            documents.append({
                'issuer_assigned_id': invoice.l10n_fr_project_reference,
                'type_code': '50',  # Project specification
            })

        # Tender reference
        if 'l10n_fr_tender_reference' in invoice._fields and invoice.l10n_fr_tender_reference:
            documents.append({
                'issuer_assigned_id': invoice.l10n_fr_tender_reference,
                'type_code': '916',  # Related document
            })

        return documents

    def _get_seller_order_reference(self, invoice):
        """Get seller order reference (BT-14)."""
        if 'l10n_fr_seller_order_reference' not in invoice._fields:
            return None
        return invoice.l10n_fr_seller_order_reference or None

    def _get_despatch_advice_reference(self, invoice):
        """Get despatch advice reference (BT-16)."""
        if 'l10n_fr_despatch_advice_reference' not in invoice._fields:
            return None
        return invoice.l10n_fr_despatch_advice_reference or None

    def _get_receiving_advice_reference(self, invoice):
        """Get receiving advice reference (BT-15)."""
        if 'l10n_fr_receiving_advice_reference' not in invoice._fields:
            return None
        return invoice.l10n_fr_receiving_advice_reference or None

    def _get_procuring_project(self, invoice):
        """Get procuring project reference (BT-11)."""
        if 'l10n_fr_procuring_project_id' in invoice._fields and invoice.l10n_fr_procuring_project_id:
            name = None
            if 'l10n_fr_procuring_project_name' in invoice._fields and invoice.l10n_fr_procuring_project_name:
                name = invoice.l10n_fr_procuring_project_name
            return {
                'id': invoice.l10n_fr_procuring_project_id,
                'name': name,
            }
        return None

    def _get_line_french_vals(self, invoice):
        """Get French-specific values for invoice lines."""
        line_vals = {}

        for line in invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product'):
            vals = {}

            # Line notes with subject code
            if 'l10n_fr_line_note' in line._fields and line.l10n_fr_line_note:
                subject_code = 'AAI'
                if 'l10n_fr_line_note_code' in line._fields and line.l10n_fr_line_note_code:
                    subject_code = line.l10n_fr_line_note_code
                vals['note'] = {
                    'content': line.l10n_fr_line_note,
                    'subject_code': subject_code,
                }

            # Buyer assigned ID (BT-156)
            if 'l10n_fr_buyer_assigned_id' in line._fields and line.l10n_fr_buyer_assigned_id:
                vals['buyer_assigned_id'] = line.l10n_fr_buyer_assigned_id

            # Buyer order line reference (BT-132)
            if 'l10n_fr_buyer_order_line_ref' in line._fields and line.l10n_fr_buyer_order_line_ref:
                vals['buyer_order_line_reference'] = line.l10n_fr_buyer_order_line_ref

            # Product origin country (BT-159)
            if 'l10n_fr_origin_country_id' in line._fields and line.l10n_fr_origin_country_id:
                vals['origin_country'] = line.l10n_fr_origin_country_id.code

            # Buyer accounting reference (BT-133)
            if 'l10n_fr_buyer_accounting_ref' in line._fields and line.l10n_fr_buyer_accounting_ref:
                vals['buyer_accounting_reference'] = line.l10n_fr_buyer_accounting_ref

            if vals:
                line_vals[line.id] = vals

        return line_vals

    # -------------------------------------------------------------------------
    # EXPORT: XML Modifications
    # -------------------------------------------------------------------------

    def _update_document_context(self, tree):
        """Update the document context ID to France CIUS."""
        context_id = tree.find('.//ram:GuidelineSpecifiedDocumentContextParameter/ram:ID', CII_NAMESPACES)
        if context_id is not None:
            context_id.text = self._get_document_context_id()

    def _apply_french_modifications(self, tree, fr_vals, invoice):
        """Apply all French-specific modifications to the XML tree."""
        # Add French notes with subject codes (including mandatory ones)
        self._add_french_notes(tree, fr_vals.get('fr_notes', []), invoice)

        # Fix SIREN in SellerTradeParty (BT-30: must be 9 digits, not SIRET 14 digits)
        self._fix_seller_siren(tree, invoice)

        # Modify seller trade party
        seller_party = tree.find('.//ram:SellerTradeParty', CII_NAMESPACES)
        if seller_party is not None:
            self._modify_trade_party(seller_party, fr_vals.get('seller_vals', {}))
            # Add BT-34: Seller electronic address (mandatory for France)
            self._add_electronic_address(seller_party, invoice.company_id.partner_id)

        # Modify buyer trade party
        buyer_party = tree.find('.//ram:BuyerTradeParty', CII_NAMESPACES)
        if buyer_party is not None:
            self._modify_trade_party(buyer_party, fr_vals.get('buyer_vals', {}))
            # Add BT-49: Buyer electronic address (mandatory for France)
            self._add_electronic_address(buyer_party, invoice.commercial_partner_id)

        # Modify ship-to trade party - remove DefinedTradeContact [CII-SR-312]
        ship_to_party = tree.find('.//ram:ShipToTradeParty', CII_NAMESPACES)
        if ship_to_party is not None:
            # Remove DefinedTradeContact from ShipToTradeParty (not allowed in EN16931)
            contact = ship_to_party.find('ram:DefinedTradeContact', CII_NAMESPACES)
            if contact is not None:
                ship_to_party.remove(contact)
            self._modify_trade_party(ship_to_party, fr_vals.get('ship_to_vals', {}))

        # Add tax representative party
        if fr_vals.get('tax_representative_vals'):
            self._add_tax_representative(tree, fr_vals['tax_representative_vals'])

        # Add payee party
        if fr_vals.get('payee_vals'):
            self._add_payee_party(tree, fr_vals['payee_vals'])

        # Add seller order reference
        if fr_vals.get('seller_order_reference'):
            self._add_seller_order_reference(tree, fr_vals['seller_order_reference'])

        # Add additional referenced documents
        if fr_vals.get('additional_documents'):
            self._add_additional_documents(tree, fr_vals['additional_documents'])

        # Add despatch advice reference
        if fr_vals.get('despatch_advice_reference'):
            self._add_despatch_advice_reference(tree, fr_vals['despatch_advice_reference'])

        # Add receiving advice reference
        if fr_vals.get('receiving_advice_reference'):
            self._add_receiving_advice_reference(tree, fr_vals['receiving_advice_reference'])

        # Add procuring project
        if fr_vals.get('procuring_project'):
            self._add_procuring_project(tree, fr_vals['procuring_project'])

        # Modify invoice lines
        self._modify_invoice_lines(tree, fr_vals.get('line_vals', {}), invoice)

    def _add_french_notes(self, tree, notes, invoice):
        """Add French notes with subject codes to ExchangedDocument.

        Includes mandatory French notes [BR-FR-05]:
        - PMT: frais de recouvrement
        - PMD: pénalités de retard
        - AAB: escompte
        """
        exchanged_doc = tree.find('.//rsm:ExchangedDocument', CII_NAMESPACES)
        if exchanged_doc is None:
            return

        # Find existing IncludedNote to add SubjectCode if needed
        existing_note = exchanged_doc.find('ram:IncludedNote', CII_NAMESPACES)
        existing_codes = set()
        if existing_note is not None:
            content = existing_note.find('ram:Content', CII_NAMESPACES)
            if content is not None and content.text:
                # Check if we should add a SubjectCode based on content pattern
                # Pattern: #CODE#content
                match = re.match(r'^#([A-Z]{3})#(.*)$', content.text or '', re.DOTALL)
                if match:
                    code, text = match.groups()
                    content.text = text
                    subject_code = _make_elem('ram:SubjectCode', code)
                    existing_note.append(subject_code)
                    existing_codes.add(code)

        # Collect subject codes from provided notes
        for note in notes:
            if note.get('subject_code'):
                existing_codes.add(note['subject_code'])

        # Add additional notes
        for note in notes:
            included_note = _make_elem('ram:IncludedNote')
            content = _make_elem('ram:Content', note.get('content'))
            included_note.append(content)
            if note.get('subject_code'):
                subject_code = _make_elem('ram:SubjectCode', note['subject_code'])
                included_note.append(subject_code)
            exchanged_doc.append(included_note)

        # Add mandatory French notes if not already present [BR-FR-05]
        mandatory_notes = self._get_mandatory_french_notes(invoice)
        for note in mandatory_notes:
            if note['subject_code'] not in existing_codes:
                included_note = _make_elem('ram:IncludedNote')
                content = _make_elem('ram:Content', note['content'])
                included_note.append(content)
                subject_code = _make_elem('ram:SubjectCode', note['subject_code'])
                included_note.append(subject_code)
                exchanged_doc.append(included_note)

    def _get_mandatory_french_notes(self, invoice):
        """Get mandatory French notes with default values [BR-FR-05]."""
        notes = []

        # PMT - Frais de recouvrement (collection costs)
        pmt_content = None
        if 'l10n_fr_note_pmt' in invoice._fields and invoice.l10n_fr_note_pmt:
            pmt_content = invoice.l10n_fr_note_pmt
        if not pmt_content:
            pmt_content = (
                "En cas de retard de paiement, une indemnité forfaitaire de 40€ pour frais de recouvrement sera "
                "exigée (Art. L441-10 et D441-5 du Code de Commerce)."
            )
        notes.append({'subject_code': 'PMT', 'content': pmt_content})

        # PMD - Pénalités de retard (late payment penalties)
        pmd_content = None
        if 'l10n_fr_note_pmd' in invoice._fields and invoice.l10n_fr_note_pmd:
            pmd_content = invoice.l10n_fr_note_pmd
        if not pmd_content:
            # Default: 3 times the legal interest rate
            pmd_content = "Pénalités de retard : taux BCE majoré de 10 points."
        notes.append({'subject_code': 'PMD', 'content': pmd_content})

        # AAB - Escompte (cash discount)
        aab_content = None
        if 'l10n_fr_note_aab' in invoice._fields and invoice.l10n_fr_note_aab:
            aab_content = invoice.l10n_fr_note_aab
        if not aab_content:
            aab_content = "Pas d'escompte pour paiement anticipé."
        notes.append({'subject_code': 'AAB', 'content': aab_content})

        return notes

    def _fix_seller_siren(self, tree, invoice):
        """Fix seller SIREN to be 9 digits [BR-FR-10/BT-30].

        The SpecifiedLegalOrganization/ID must contain SIREN (9 digits),
        not SIRET (14 digits).
        """
        seller_party = tree.find('.//ram:SellerTradeParty', CII_NAMESPACES)
        if seller_party is None:
            return

        legal_org = seller_party.find('ram:SpecifiedLegalOrganization', CII_NAMESPACES)
        if legal_org is None:
            return

        org_id = legal_org.find('ram:ID', CII_NAMESPACES)
        if org_id is not None and org_id.text:
            # If SIRET (14 digits), extract SIREN (first 9 digits)
            siret_value = org_id.text.strip()
            if len(siret_value) == 14 and siret_value.isdigit():
                org_id.text = siret_value[:9]  # SIREN = first 9 digits of SIRET

    def _add_electronic_address(self, party_elem, partner):
        """Add URIUniversalCommunication (BT-34 for seller, BT-49 for buyer).

        Mandatory for French e-invoicing [BR-FR-12, BR-FR-13].
        Only explicit identifiers are accepted (no guessed fallback values).
        """
        # Check if URIUniversalCommunication already exists
        existing_uri = party_elem.find('ram:URIUniversalCommunication', CII_NAMESPACES)
        if existing_uri is not None:
            return  # Already present

        address_vals, _error_msg = self._get_partner_electronic_address(partner)
        if not address_vals:
            return

        uri_comm = _make_elem('ram:URIUniversalCommunication')
        uri_id = _make_elem('ram:URIID', address_vals['uri_id'])
        uri_id.set('schemeID', address_vals['scheme_id'])
        uri_comm.append(uri_id)
        # Insert before SpecifiedTaxRegistration
        tax_reg = party_elem.find('ram:SpecifiedTaxRegistration', CII_NAMESPACES)
        if tax_reg is not None:
            idx = list(party_elem).index(tax_reg)
            party_elem.insert(idx, uri_comm)
        else:
            party_elem.append(uri_comm)

    def _get_partner_electronic_address(self, partner):
        """Resolve URIID/schemeID from explicit business identifiers only."""
        commercial_partner = partner.commercial_partner_id or partner

        if 'l10n_fr_uri_id' in commercial_partner._fields and commercial_partner.l10n_fr_uri_id:
            uri_id = commercial_partner.l10n_fr_uri_id.strip()
            uri_scheme_id = (
                commercial_partner.l10n_fr_uri_scheme_id.strip()
                if 'l10n_fr_uri_scheme_id' in commercial_partner._fields and commercial_partner.l10n_fr_uri_scheme_id
                else ''
            )
            if uri_scheme_id:
                return {'uri_id': uri_id, 'scheme_id': uri_scheme_id}, None
            return None, _("custom URI is set but URI scheme is missing")

        if 'peppol_endpoint' in commercial_partner._fields and commercial_partner.peppol_endpoint:
            uri_id = commercial_partner.peppol_endpoint.strip()
            uri_scheme_id = (
                commercial_partner.peppol_eas.strip()
                if 'peppol_eas' in commercial_partner._fields and commercial_partner.peppol_eas
                else ''
            )
            if uri_scheme_id:
                return {'uri_id': uri_id, 'scheme_id': uri_scheme_id}, None
            return None, _("Peppol endpoint is set but EAS scheme is missing")

        siret_value = (
            commercial_partner.siret.strip()
            if 'siret' in commercial_partner._fields and commercial_partner.siret
            else ''
        )
        if siret_value:
            if len(siret_value) == 14 and siret_value.isdigit():
                return {'uri_id': siret_value, 'scheme_id': '0009'}, None
            if len(siret_value) == 9 and siret_value.isdigit():
                return {'uri_id': siret_value, 'scheme_id': '0002'}, None
            return None, _("SIRET/SIREN has an invalid format")

        registry = commercial_partner.company_registry.strip() if commercial_partner.company_registry else ''
        if registry:
            if len(registry) == 14 and registry.isdigit():
                return {'uri_id': registry, 'scheme_id': '0009'}, None
            if len(registry) == 9 and registry.isdigit():
                return {'uri_id': registry, 'scheme_id': '0002'}, None
            return None, _("company registry has an invalid format")

        return None, _("no explicit electronic address identifier is configured")

    def _check_mandatory_electronic_addresses(self, invoice):
        """Return explicit export errors for mandatory BT-34 / BT-49 data."""
        checks = (
            ('BT-34', _('seller'), invoice.company_id.partner_id),
            ('BT-49', _('buyer'), invoice.commercial_partner_id),
        )
        errors = set()
        for bt_code, role_label, partner in checks:
            _vals, error_msg = self._get_partner_electronic_address(partner)
            if error_msg:
                errors.add(
                    _(
                        "%(bt_code)s (%(role)s): %(partner)s -> %(reason)s",
                        bt_code=bt_code,
                        role=role_label,
                        partner=partner.display_name,
                        reason=error_msg,
                    )
                )
        return errors

    def _modify_trade_party(self, party_elem, vals):
        """Modify a trade party element with French-specific values."""
        if not vals:
            return

        # Add Description (Legal Form) after Name
        if vals.get('description'):
            name_elem = party_elem.find('ram:Name', CII_NAMESPACES)
            if name_elem is not None:
                desc_elem = _make_elem('ram:Description', vals['description'])
                idx = list(party_elem).index(name_elem)
                party_elem.insert(idx + 1, desc_elem)

        # Add TradingBusinessName in SpecifiedLegalOrganization
        if vals.get('trading_business_name'):
            legal_org = party_elem.find('ram:SpecifiedLegalOrganization', CII_NAMESPACES)
            if legal_org is not None:
                trading_name = _make_elem('ram:TradingBusinessName', vals['trading_business_name'])
                legal_org.append(trading_name)

        # Add DepartmentName in DefinedTradeContact
        if vals.get('department_name'):
            contact = party_elem.find('ram:DefinedTradeContact', CII_NAMESPACES)
            if contact is not None:
                person_name = contact.find('ram:PersonName', CII_NAMESPACES)
                if person_name is not None:
                    dept_elem = _make_elem('ram:DepartmentName', vals['department_name'])
                    idx = list(contact).index(person_name)
                    contact.insert(idx + 1, dept_elem)

        # Modify PostalTradeAddress
        address = party_elem.find('ram:PostalTradeAddress', CII_NAMESPACES)
        if address is not None:
            # Add LineThree after LineTwo
            if vals.get('street3'):
                line_two = address.find('ram:LineTwo', CII_NAMESPACES)
                if line_two is not None:
                    line_three = _make_elem('ram:LineThree', vals['street3'])
                    idx = list(address).index(line_two)
                    address.insert(idx + 1, line_three)

            # Add CountrySubDivisionName after CountryID
            if vals.get('country_subdivision_name'):
                country_id = address.find('ram:CountryID', CII_NAMESPACES)
                if country_id is not None:
                    subdiv = _make_elem('ram:CountrySubDivisionName', vals['country_subdivision_name'])
                    idx = list(address).index(country_id)
                    address.insert(idx + 1, subdiv)

        # Add URIUniversalCommunication (only if not already present)
        if vals.get('uri_id'):
            existing_uri = party_elem.find('ram:URIUniversalCommunication', CII_NAMESPACES)
            if existing_uri is None:
                uri_comm = _make_elem('ram:URIUniversalCommunication')
                uri_id = _make_elem('ram:URIID', vals['uri_id'])
                if vals.get('uri_scheme_id'):
                    uri_id.set('schemeID', vals['uri_scheme_id'])
                uri_comm.append(uri_id)

                # Insert before SpecifiedTaxRegistration
                tax_reg = party_elem.find('ram:SpecifiedTaxRegistration', CII_NAMESPACES)
                if tax_reg is not None:
                    idx = list(party_elem).index(tax_reg)
                    party_elem.insert(idx, uri_comm)
                else:
                    party_elem.append(uri_comm)

    def _add_tax_representative(self, tree, vals):
        """Add SellerTaxRepresentativeTradeParty (BG-11)."""
        agreement = tree.find('.//ram:ApplicableHeaderTradeAgreement', CII_NAMESPACES)
        if agreement is None:
            return

        rep_party = _make_elem('ram:SellerTaxRepresentativeTradeParty')

        # Name
        rep_party.append(_make_elem('ram:Name', vals.get('name')))

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
        rep_party.append(address)

        # Tax Registration
        if vals.get('vat'):
            tax_reg = _make_elem('ram:SpecifiedTaxRegistration')
            tax_id = _make_elem('ram:ID', vals['vat'])
            tax_id.set('schemeID', 'VA')
            tax_reg.append(tax_id)
            rep_party.append(tax_reg)

        # Insert after BuyerTradeParty
        buyer = agreement.find('ram:BuyerTradeParty', CII_NAMESPACES)
        if buyer is not None:
            idx = list(agreement).index(buyer)
            agreement.insert(idx + 1, rep_party)
        else:
            agreement.append(rep_party)

    def _add_payee_party(self, tree, vals):
        """Add PayeeTradeParty (BG-10)."""
        settlement = tree.find('.//ram:ApplicableHeaderTradeSettlement', CII_NAMESPACES)
        if settlement is None:
            return

        payee = _make_elem('ram:PayeeTradeParty')

        # ID
        if vals.get('id'):
            payee.append(_make_elem('ram:ID', vals['id']))

        # Global IDs
        for gid in vals.get('global_ids', []):
            global_id = _make_elem('ram:GlobalID', gid.get('id'))
            if gid.get('scheme_id'):
                global_id.set('schemeID', gid['scheme_id'])
            payee.append(global_id)

        # Name
        if vals.get('name'):
            payee.append(_make_elem('ram:Name', vals['name']))

        # Legal Organization
        if vals.get('legal_org_id'):
            legal_org = _make_elem('ram:SpecifiedLegalOrganization')
            org_id = _make_elem('ram:ID', vals['legal_org_id'])
            if vals.get('legal_org_scheme'):
                org_id.set('schemeID', vals['legal_org_scheme'])
            legal_org.append(org_id)
            payee.append(legal_org)

        # Insert after PaymentReference
        payment_ref = settlement.find('ram:PaymentReference', CII_NAMESPACES)
        if payment_ref is not None:
            idx = list(settlement).index(payment_ref)
            settlement.insert(idx + 1, payee)
        else:
            settlement.insert(0, payee)

    def _add_seller_order_reference(self, tree, reference):
        """Add SellerOrderReferencedDocument (BT-14)."""
        agreement = tree.find('.//ram:ApplicableHeaderTradeAgreement', CII_NAMESPACES)
        if agreement is None:
            return

        seller_order = _make_elem('ram:SellerOrderReferencedDocument')
        seller_order.append(_make_elem('ram:IssuerAssignedID', reference))

        # Insert after BuyerOrderReferencedDocument
        buyer_order = agreement.find('ram:BuyerOrderReferencedDocument', CII_NAMESPACES)
        if buyer_order is not None:
            idx = list(agreement).index(buyer_order)
            agreement.insert(idx + 1, seller_order)
        else:
            agreement.append(seller_order)

    def _add_additional_documents(self, tree, documents):
        """Add AdditionalReferencedDocument elements (BG-24)."""
        if not documents:
            return

        agreement = tree.find('.//ram:ApplicableHeaderTradeAgreement', CII_NAMESPACES)
        if agreement is None:
            return

        for doc in documents:
            add_doc = _make_elem('ram:AdditionalReferencedDocument')
            add_doc.append(_make_elem('ram:IssuerAssignedID', doc.get('issuer_assigned_id')))
            if doc.get('uri_id'):
                add_doc.append(_make_elem('ram:URIID', doc['uri_id']))
            if doc.get('type_code'):
                add_doc.append(_make_elem('ram:TypeCode', doc['type_code']))
            if doc.get('name'):
                add_doc.append(_make_elem('ram:Name', doc['name']))
            agreement.append(add_doc)

    def _add_despatch_advice_reference(self, tree, reference):
        """Add DespatchAdviceReferencedDocument (BT-16)."""
        delivery = tree.find('.//ram:ApplicableHeaderTradeDelivery', CII_NAMESPACES)
        if delivery is None:
            return

        despatch = _make_elem('ram:DespatchAdviceReferencedDocument')
        despatch.append(_make_elem('ram:IssuerAssignedID', reference))
        delivery.append(despatch)

    def _add_receiving_advice_reference(self, tree, reference):
        """Add ReceivingAdviceReferencedDocument (BT-15)."""
        delivery = tree.find('.//ram:ApplicableHeaderTradeDelivery', CII_NAMESPACES)
        if delivery is None:
            return

        receiving = _make_elem('ram:ReceivingAdviceReferencedDocument')
        receiving.append(_make_elem('ram:IssuerAssignedID', reference))
        delivery.append(receiving)

    def _add_procuring_project(self, tree, project):
        """Add SpecifiedProcuringProject (BT-11)."""
        agreement = tree.find('.//ram:ApplicableHeaderTradeAgreement', CII_NAMESPACES)
        if agreement is None:
            return

        proc_project = _make_elem('ram:SpecifiedProcuringProject')
        proc_project.append(_make_elem('ram:ID', project.get('id')))
        if project.get('name'):
            proc_project.append(_make_elem('ram:Name', project['name']))
        agreement.append(proc_project)

    def _modify_invoice_lines(self, tree, line_vals_dict, invoice):
        """Modify invoice lines with French-specific values."""
        if not line_vals_dict:
            return

        lines = tree.findall('.//ram:IncludedSupplyChainTradeLineItem', CII_NAMESPACES)

        for idx, line_elem in enumerate(lines):
            # Find corresponding invoice line
            line_id_elem = line_elem.find('.//ram:LineID', CII_NAMESPACES)
            if line_id_elem is None:
                continue

            # Get line vals by matching index (lines are in order)
            invoice_lines = invoice.invoice_line_ids.filtered(lambda l: l.display_type == 'product')
            if idx >= len(invoice_lines):
                continue

            invoice_line = invoice_lines[idx]
            vals = line_vals_dict.get(invoice_line.id, {})

            if not vals:
                continue

            # Add line note with subject code
            if vals.get('note'):
                doc = line_elem.find('ram:AssociatedDocumentLineDocument', CII_NAMESPACES)
                if doc is not None:
                    note = _make_elem('ram:IncludedNote')
                    note.append(_make_elem('ram:Content', vals['note']['content']))
                    if vals['note'].get('subject_code'):
                        note.append(_make_elem('ram:SubjectCode', vals['note']['subject_code']))
                    doc.append(note)

            # Add BuyerAssignedID
            if vals.get('buyer_assigned_id'):
                product = line_elem.find('ram:SpecifiedTradeProduct', CII_NAMESPACES)
                if product is not None:
                    # Insert at beginning, before GlobalID
                    buyer_id = _make_elem('ram:BuyerAssignedID', vals['buyer_assigned_id'])
                    product.insert(0, buyer_id)

            # Add BuyerOrderReferencedDocument with LineID
            if vals.get('buyer_order_line_reference'):
                agreement = line_elem.find('ram:SpecifiedLineTradeAgreement', CII_NAMESPACES)
                if agreement is not None:
                    buyer_order = _make_elem('ram:BuyerOrderReferencedDocument')
                    buyer_order.append(_make_elem('ram:LineID', vals['buyer_order_line_reference']))
                    agreement.insert(0, buyer_order)

            # Add OriginTradeCountry
            if vals.get('origin_country'):
                product = line_elem.find('ram:SpecifiedTradeProduct', CII_NAMESPACES)
                if product is not None:
                    origin = _make_elem('ram:OriginTradeCountry')
                    origin.append(_make_elem('ram:ID', vals['origin_country']))
                    product.append(origin)

            # Add ReceivableSpecifiedTradeAccountingAccount
            if vals.get('buyer_accounting_reference'):
                settlement = line_elem.find('ram:SpecifiedLineTradeSettlement', CII_NAMESPACES)
                if settlement is not None:
                    account = _make_elem('ram:ReceivableSpecifiedTradeAccountingAccount')
                    account.append(_make_elem('ram:ID', vals['buyer_accounting_reference']))
                    settlement.append(account)

    # -------------------------------------------------------------------------
    # IMPORT: French-specific
    # -------------------------------------------------------------------------

    # French billing modes for detection
    FR_BILLING_MODES = ['B1', 'S1', 'M1', 'B2', 'S2', 'M2', 'B4', 'S4', 'M4', 'S5', 'S6', 'B7', 'S7']

    def _is_french_invoice(self, tree):
        """Detect if the invoice is a French CIUS invoice."""
        # Check for French notes pattern (#PMT#, #PMD#, #AAB#)
        notes = tree.findall('.//ram:IncludedNote/ram:Content', CII_NAMESPACES)
        for note in notes:
            if note.text:
                for code in ('PMT', 'PMD', 'AAB'):
                    if f'#{code}#' in note.text:
                        return True

        # Check for SubjectCode in IncludedNote (French-specific)
        subject_codes = tree.findall('.//ram:IncludedNote/ram:SubjectCode', CII_NAMESPACES)
        if subject_codes:
            for sc in subject_codes:
                if sc.text and sc.text.strip() in ('PMT', 'PMD', 'AAB', 'AAI', 'ABL', 'ACC', 'BLU', 'DCL', 'SUR', 'TXD'):
                    return True

        # Check seller country
        seller_country = tree.findtext('.//ram:SellerTradeParty/ram:PostalTradeAddress/ram:CountryID', namespaces=CII_NAMESPACES)
        if seller_country and seller_country.strip() == 'FR':
            return True

        # Check GuidelineSpecifiedDocumentContextParameter for French CIUS
        guideline_id = tree.findtext('.//ram:GuidelineSpecifiedDocumentContextParameter/ram:ID', namespaces=CII_NAMESPACES)
        if guideline_id and 'en16931' in guideline_id.lower():
            # Check if seller is French
            seller_vat = tree.findtext('.//ram:SellerTradeParty//ram:SpecifiedTaxRegistration/ram:ID', namespaces=CII_NAMESPACES)
            if seller_vat and seller_vat.strip().startswith('FR'):
                return True

        return False

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        """Override to add French-specific import logic."""
        # Call parent import first
        logs = super()._import_fill_invoice(invoice, tree, qty_factor)

        # Only process French-specific data if this is a French invoice
        if not self._is_french_invoice(tree):
            return logs

        # Import French-specific fields
        logs += self._import_french_fields(invoice, tree)

        return logs

    def _import_french_fields(self, invoice, tree):
        """Import French-specific fields from CII."""
        logs = []
        invoice_values = {}

        # Import French notes with subject codes
        notes_imported = self._import_french_notes(invoice, tree, invoice_values)
        if notes_imported:
            logs.append(f"Notes françaises importées: {', '.join(notes_imported)}")

        # Import SIREN from seller
        siren = self._import_french_siren(tree, 'SellerTradeParty')
        if siren:
            logs.append(f"SIREN vendeur détecté: {siren}")

        # Import seller electronic address
        seller_uri = self._import_electronic_address(tree, 'SellerTradeParty')
        if seller_uri:
            logs.append(f"Adresse électronique vendeur: {seller_uri.get('uri_id', '')} (schéma: {seller_uri.get('scheme_id', '')})")

        # Import buyer electronic address
        buyer_uri = self._import_electronic_address(tree, 'BuyerTradeParty')
        if buyer_uri:
            logs.append(f"Adresse électronique acheteur: {buyer_uri.get('uri_id', '')} (schéma: {buyer_uri.get('scheme_id', '')})")

        # Write invoice values if any
        if invoice_values:
            invoice.write(invoice_values)

        return logs

    def _import_french_notes(self, invoice, tree, invoice_values):
        """Parse French notes with subject codes."""
        imported_codes = []

        # Map of subject codes to field names
        code_to_field = {
            'AAB': 'l10n_fr_note_aab',
            'AAI': 'l10n_fr_note_aai',
            'ABL': 'l10n_fr_note_abl',
            'ACC': 'l10n_fr_note_acc',
            'BLU': 'l10n_fr_note_blu',
            'DCL': 'l10n_fr_note_dcl',
            'PMT': 'l10n_fr_note_pmt',
            'PMD': 'l10n_fr_note_pmd',
            'SUR': 'l10n_fr_note_sur',
            'TXD': 'l10n_fr_note_txd',
        }

        # Find all IncludedNote elements
        notes = tree.findall('.//rsm:ExchangedDocument/ram:IncludedNote', CII_NAMESPACES)

        for note_elem in notes:
            content_elem = note_elem.find('ram:Content', CII_NAMESPACES)
            subject_code_elem = note_elem.find('ram:SubjectCode', CII_NAMESPACES)

            if content_elem is None or content_elem.text is None:
                continue

            content = content_elem.text.strip()
            code = None

            # Check if subject code is in a separate element
            if subject_code_elem is not None and subject_code_elem.text:
                code = subject_code_elem.text.strip()
            # Or check if content starts with #CODE# pattern
            elif content.startswith('#') and '#' in content[1:]:
                match = re.match(r'^#([A-Z]{3})#(.*)$', content, re.DOTALL)
                if match:
                    code = match.group(1)
                    content = match.group(2).strip()

            if code and code in code_to_field:
                field_name = code_to_field[code]
                if field_name not in invoice._fields:
                    continue
                invoice_values[field_name] = content
                imported_codes.append(code)

        return imported_codes

    def _import_french_siren(self, tree, party_type):
        """Extract SIREN from SpecifiedLegalOrganization/ID."""
        # Look for SpecifiedLegalOrganization ID with schemeID='0002'
        xpath = f'.//ram:{party_type}/ram:SpecifiedLegalOrganization/ram:ID'
        org_ids = tree.findall(xpath, CII_NAMESPACES)

        for org_id in org_ids:
            scheme_id = org_id.get('schemeID')
            if org_id.text:
                value = org_id.text.strip()
                # SIREN is 9 digits
                if len(value) == 9 and value.isdigit():
                    return value
                # SIRET is 14 digits - extract SIREN
                elif len(value) == 14 and value.isdigit():
                    return value[:9]
                # schemeID='0002' indicates SIREN/SIRET
                elif scheme_id == '0002':
                    if len(value) >= 9 and value[:9].isdigit():
                        return value[:9]

        return None

    def _import_electronic_address(self, tree, party_type):
        """Extract URIUniversalCommunication (BT-34/BT-49)."""
        xpath = f'.//ram:{party_type}/ram:URIUniversalCommunication/ram:URIID'
        uri_elem = tree.find(xpath, CII_NAMESPACES)

        if uri_elem is not None and uri_elem.text:
            return {
                'uri_id': uri_elem.text.strip(),
                'scheme_id': uri_elem.get('schemeID', ''),
            }

        return None

    def _import_retrieve_partner_vals(self, tree, role):
        """Override to add French-specific partner retrieval."""
        vals = super()._import_retrieve_partner_vals(tree, role)

        # Map CII role to party type
        party_type_map = {
            'SellerTradeParty': 'SellerTradeParty',
            'BuyerTradeParty': 'BuyerTradeParty',
        }
        party_type = party_type_map.get(role, role)

        # Try to get peppol info from URIUniversalCommunication
        uri_info = self._import_electronic_address(tree, party_type)
        if uri_info and uri_info.get('uri_id') and uri_info.get('scheme_id'):
            vals['peppol_endpoint'] = uri_info['uri_id']
            vals['peppol_eas'] = uri_info['scheme_id']

        return vals

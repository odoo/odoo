from odoo import models
from odoo.addons.account_edi_ubl_cii.models.account_edi_xml_ubl_20 import UBL_NAMESPACES

# French billing modes (BT-23 / ProfileID) for CIUS FR
# B = B2B, S = B2G, M = Mixed
# 1 = Domestic, 2 = Intracom, 4 = Export, 5/6/7 = Special cases
FR_BILLING_MODES = ['B1', 'S1', 'M1', 'B2', 'S2', 'M2', 'B4', 'S4', 'M4', 'S5', 'S6', 'B7', 'S7']

# Default French notes content [BR-FR-05]
FR_DEFAULT_NOTES = {
    'PMT': "En cas de retard de paiement, une indemnité forfaitaire de 40€ pour frais de recouvrement sera exigée (art. L.441-10 et D.441-5 du Code de commerce).",
    'PMD': "Pénalités de retard au taux annuel de 10% en cas de paiement après la date d'échéance.",
    'AAB': "Pas d'escompte pour paiement anticipé.",
}


class AccountEdiXmlUblFr(models.AbstractModel):
    _name = "account.edi.xml.ubl_fr"
    _inherit = "account.edi.xml.ubl_bis3"
    _description = "UBL France CIUS EN16931"

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_fr.xml"

    def _get_customization_ids(self):
        vals = super()._get_customization_ids()
        vals['ubl_fr'] = 'urn:cen.eu:en16931:2017'
        return vals

    # -------------------------------------------------------------------------
    # EXPORT: Invoice Header Nodes
    # -------------------------------------------------------------------------

    def _get_french_billing_mode(self, invoice):
        """Compute the French billing mode (BT-23 / ProfileID)."""
        # Check if invoice has a specific billing mode set
        if 'l10n_fr_billing_mode' in invoice._fields and invoice.l10n_fr_billing_mode:
            return invoice.l10n_fr_billing_mode

        # Determine based on customer type
        customer = invoice.commercial_partner_id
        is_public_sector = (
            bool(customer.is_public_sector)
            if 'is_public_sector' in customer._fields
            else False
        )

        # Determine geography
        supplier_country = invoice.company_id.country_id.code
        customer_country = customer.country_id.code

        # Check if intracom (EU)
        eu_countries = self.env.ref('base.europe').country_ids.mapped('code')
        is_intracom = (
            supplier_country in eu_countries
            and customer_country in eu_countries
            and supplier_country != customer_country
        )

        # Check if export (non-EU)
        is_export = customer_country and customer_country not in eu_countries

        # Build billing mode
        prefix = 'S' if is_public_sector else 'B'  # B = B2B, S = B2G
        if is_export:
            suffix = '4'
        elif is_intracom:
            suffix = '2'
        else:
            suffix = '1'  # Domestic

        return f"{prefix}{suffix}"

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        # Override CustomizationID for EN16931
        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_ids()['ubl_fr']}

        # [BR-FR-08] Override ProfileID with French billing mode
        billing_mode = self._get_french_billing_mode(invoice)
        document_node['cbc:ProfileID'] = {'_text': billing_mode}

        # BT-7: TaxPointDate
        if 'l10n_fr_tax_point_date' in invoice._fields and invoice.l10n_fr_tax_point_date:
            document_node['cbc:TaxPointDate'] = {'_text': invoice.l10n_fr_tax_point_date.isoformat()}

        # BT-19: AccountingCost (buyer's accounting reference)
        if 'l10n_fr_accounting_cost' in invoice._fields and invoice.l10n_fr_accounting_cost:
            document_node['cbc:AccountingCost'] = {'_text': invoice.l10n_fr_accounting_cost}

        # Add French-specific notes with SubjectCode
        self._add_french_notes(document_node, invoice)

        # Add document references
        self._add_document_references(document_node, invoice)

    def _add_french_notes(self, document_node, invoice):
        """Add French-specific notes with SubjectCode (BT-21).

        [BR-FR-05] Mandatory notes PMT, PMD, AAB must be present.
        """
        # Map of field names to note codes
        note_fields = {
            'l10n_fr_note_aab': 'AAB',  # Cash Discount
            'l10n_fr_note_aai': 'AAI',  # General Info
            'l10n_fr_note_abl': 'ABL',  # Legal Info
            'l10n_fr_note_acc': 'ACC',  # Factoring Clause
            'l10n_fr_note_blu': 'BLU',  # Eco-participation
            'l10n_fr_note_dcl': 'DCL',  # Invoice Creator Declaration
            'l10n_fr_note_pmt': 'PMT',  # 40€ Recovery Fee
            'l10n_fr_note_pmd': 'PMD',  # Late Payment Penalties
            'l10n_fr_note_sur': 'SUR',  # Supplier Remarks
            'l10n_fr_note_txd': 'TXD',  # Single Taxable Person
        }

        # Initialize notes list if not already done
        if 'cbc:Note' not in document_node or not isinstance(document_node.get('cbc:Note'), list):
            existing_note = document_node.get('cbc:Note')
            document_node['cbc:Note'] = [existing_note] if existing_note else []

        # Track which codes have been added
        added_codes = set()

        # First, add notes from invoice fields (if they exist and have content)
        for field_name, code in note_fields.items():
            if field_name not in invoice._fields:
                continue
            content = invoice[field_name]
            if content:
                # Format: #CODE#Content as per EN16931
                document_node['cbc:Note'].append({
                    '_text': f"#{code}#{content}"
                })
                added_codes.add(code)

        # [BR-FR-05] Add mandatory notes with defaults if not already present
        for code, default_content in FR_DEFAULT_NOTES.items():
            if code not in added_codes:
                document_node['cbc:Note'].append({
                    '_text': f"#{code}#{default_content}"
                })

    def _add_document_references(self, document_node, invoice):
        """Add document-level references (BT-12 to BT-17)."""
        # BT-12: ContractDocumentReference
        if 'l10n_fr_contract_reference' in invoice._fields and invoice.l10n_fr_contract_reference:
            document_node['cac:ContractDocumentReference'] = {
                'cbc:ID': {'_text': invoice.l10n_fr_contract_reference}
            }

        # BT-15: ReceiptDocumentReference
        if 'l10n_fr_receipt_reference' in invoice._fields and invoice.l10n_fr_receipt_reference:
            document_node['cac:ReceiptDocumentReference'] = {
                'cbc:ID': {'_text': invoice.l10n_fr_receipt_reference}
            }

        # BT-16: DespatchDocumentReference
        if 'l10n_fr_despatch_reference' in invoice._fields and invoice.l10n_fr_despatch_reference:
            document_node['cac:DespatchDocumentReference'] = {
                'cbc:ID': {'_text': invoice.l10n_fr_despatch_reference}
            }

        # BT-17: OriginatorDocumentReference
        if 'l10n_fr_originator_reference' in invoice._fields and invoice.l10n_fr_originator_reference:
            document_node['cac:OriginatorDocumentReference'] = {
                'cbc:ID': {'_text': invoice.l10n_fr_originator_reference}
            }

    # -------------------------------------------------------------------------
    # EXPORT: Party Nodes
    # -------------------------------------------------------------------------

    def _get_siren_from_partner(self, partner):
        """Extract SIREN (9 digits) from partner's SIRET or other identifiers.

        [BR-FR-10] SIREN must be exactly 9 digits.
        SIRET = SIREN (9 digits) + NIC (5 digits) = 14 digits
        """
        commercial_partner = partner.commercial_partner_id or partner

        # Priority 1: Check siret field (l10n_fr adds this field)
        if 'siret' in commercial_partner._fields and commercial_partner.siret:
            siret = commercial_partner.siret.strip()
            if len(siret) == 14 and siret.isdigit():
                return siret[:9]  # SIREN = first 9 digits of SIRET
            elif len(siret) == 9 and siret.isdigit():
                return siret  # Already SIREN

        # Priority 2: Check company_registry
        if commercial_partner.company_registry:
            registry = commercial_partner.company_registry.strip()
            if len(registry) == 14 and registry.isdigit():
                return registry[:9]  # SIRET → SIREN
            elif len(registry) == 9 and registry.isdigit():
                return registry  # Already SIREN

        return None

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)
        partner = vals['partner'].commercial_partner_id

        # BT-33: CompanyLegalForm
        if 'l10n_fr_legal_form' in partner._fields and partner.l10n_fr_legal_form:
            if 'cac:PartyLegalEntity' not in party_node:
                party_node['cac:PartyLegalEntity'] = {}
            party_node['cac:PartyLegalEntity']['cbc:CompanyLegalForm'] = {
                '_text': partner.l10n_fr_legal_form
            }

        # BT-28/BT-45: TradingBusinessName
        if 'l10n_fr_trading_name' in partner._fields and partner.l10n_fr_trading_name:
            if 'cac:PartyLegalEntity' not in party_node:
                party_node['cac:PartyLegalEntity'] = {}
            party_node['cac:PartyLegalEntity']['cbc:RegistrationName'] = {
                '_text': partner.l10n_fr_trading_name
            }

        # [BR-FR-10] For French partners: Add SIREN with schemeID='0002'
        if partner.country_id and partner.country_id.code == 'FR':
            siren = self._get_siren_from_partner(partner)
            if siren:
                if 'cac:PartyLegalEntity' not in party_node:
                    party_node['cac:PartyLegalEntity'] = {}
                party_node['cac:PartyLegalEntity']['cbc:CompanyID'] = {
                    '_text': siren,
                    'schemeID': '0002'  # 0002 = SIREN/SIRENE
                }

        return party_node

    def _get_address_node(self, vals):
        address_node = super()._get_address_node(vals)
        partner = vals['partner']

        # BT-163: AddressLine/Line (street3)
        if 'street3' in partner._fields and partner.street3:
            address_node['cac:AddressLine'] = {
                'cbc:Line': {'_text': partner.street3}
            }

        # BT-39/54/68/79: CountrySubentity (region/state name, not code)
        # Note: parent class removes CountrySubentityCode for BIS3 compliance
        # Here we add the full name instead for EN16931
        if partner.state_id:
            address_node['cbc:CountrySubentity'] = {'_text': partner.state_id.name}

        return address_node

    # -------------------------------------------------------------------------
    # EXPORT: Tax Representative Party (BG-11)
    # -------------------------------------------------------------------------

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        super()._add_invoice_accounting_supplier_party_nodes(document_node, vals)
        invoice = vals['invoice']

        # BG-11: TaxRepresentativeParty (BT-62, BT-63)
        tax_rep = self._get_tax_representative_party(invoice)
        if tax_rep:
            document_node['cac:TaxRepresentativeParty'] = tax_rep

    def _get_tax_representative_party(self, invoice):
        """Get tax representative party if configured."""
        # Check if tax representative is configured on company
        company = invoice.company_id
        if 'l10n_fr_tax_representative_id' not in company._fields:
            return None
        tax_rep = company.l10n_fr_tax_representative_id
        if not tax_rep:
            return None

        return {
            'cac:PartyName': {
                'cbc:Name': {'_text': tax_rep.name}
            },
            'cac:PostalAddress': self._get_address_node({'partner': tax_rep}),
            'cac:PartyTaxScheme': [{
                'cbc:CompanyID': {'_text': tax_rep.vat},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT'}
                }
            }]
        }

    # -------------------------------------------------------------------------
    # EXPORT: Payee Party (BG-10)
    # -------------------------------------------------------------------------

    def _add_invoice_payee_party_nodes(self, document_node, vals):
        """Add PayeeParty if different from supplier."""
        invoice = vals['invoice']

        # Check if a separate payee is defined
        if 'l10n_fr_payee_id' not in invoice._fields or not invoice.l10n_fr_payee_id:
            return

        payee = invoice.l10n_fr_payee_id
        document_node['cac:PayeeParty'] = {
            'cac:PartyName': {
                'cbc:Name': {'_text': payee.name}
            },
            'cac:PartyIdentification': {
                'cbc:ID': {
                    '_text': payee.ref,
                    'schemeID': (
                        payee.l10n_fr_identifier_scheme or None
                        if 'l10n_fr_identifier_scheme' in payee._fields
                        else None
                    )
                }
            } if payee.ref else None,
            'cac:PartyLegalEntity': {
                'cbc:CompanyID': {
                    '_text': payee.company_registry,
                    'schemeID': '0002'
                }
            } if payee.company_registry else None,
        }

    # -------------------------------------------------------------------------
    # EXPORT: Payment Means Extensions
    # -------------------------------------------------------------------------

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        super()._add_invoice_payment_means_nodes(document_node, vals)
        invoice = vals['invoice']

        payment_means = document_node.get('cac:PaymentMeans', {})

        # BG-18: CardAccount (BT-87, BT-88)
        if 'l10n_fr_card_pan' in invoice._fields and invoice.l10n_fr_card_pan:
            payment_means['cac:CardAccount'] = {
                'cbc:PrimaryAccountNumberID': {'_text': invoice.l10n_fr_card_pan},
                'cbc:HolderName': {
                    '_text': invoice.l10n_fr_card_holder or None
                    if 'l10n_fr_card_holder' in invoice._fields
                    else None
                }
            }

        # BT-89: PaymentMandate ID (Direct Debit)
        if 'l10n_fr_mandate_id' in invoice._fields and invoice.l10n_fr_mandate_id:
            payment_means['cac:PaymentMandate'] = {
                'cbc:ID': {'_text': invoice.l10n_fr_mandate_id}
            }

        # BT-91: PayerFinancialAccount (Debited account in direct debit)
        if 'l10n_fr_payer_account' in invoice._fields and invoice.l10n_fr_payer_account:
            payment_means['cac:PayerFinancialAccount'] = {
                'cbc:ID': {'_text': invoice.l10n_fr_payer_account}
            }

    # -------------------------------------------------------------------------
    # EXPORT: Invoice Line Extensions
    # -------------------------------------------------------------------------

    def _get_invoice_line_node(self, vals):
        line_node = super()._get_invoice_line_node(vals)
        base_line = vals['base_line']
        line = base_line.get('record')

        if not line:
            return line_node

        # BT-127: Invoice line note
        if 'l10n_fr_line_note' in line._fields and line.l10n_fr_line_note:
            line_node['cbc:Note'] = {'_text': line.l10n_fr_line_note}

        # BT-128: DocumentReference (line level)
        if 'l10n_fr_document_reference' in line._fields and line.l10n_fr_document_reference:
            line_node['cac:DocumentReference'] = {
                'cbc:ID': {
                    '_text': line.l10n_fr_document_reference,
                    'schemeID': (
                        line.l10n_fr_document_reference_scheme or None
                        if 'l10n_fr_document_reference_scheme' in line._fields
                        else None
                    )
                }
            }

        # BT-132: OrderLineReference
        if 'l10n_fr_order_line_reference' in line._fields and line.l10n_fr_order_line_reference:
            line_node['cac:OrderLineReference'] = {
                'cbc:LineID': {'_text': line.l10n_fr_order_line_reference}
            }

        # BT-133: AccountingCost at line level
        if 'l10n_fr_line_accounting_cost' in line._fields and line.l10n_fr_line_accounting_cost:
            line_node['cbc:AccountingCost'] = {'_text': line.l10n_fr_line_accounting_cost}

        return line_node

    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)
        base_line = vals['base_line']
        line = base_line.get('record')

        if not line or 'cac:Item' not in line_node:
            return

        item_node = line_node['cac:Item']

        # BT-159: OriginCountry
        product = line.product_id
        if product and 'l10n_fr_origin_country_id' in product._fields and product.l10n_fr_origin_country_id:
            item_node['cac:OriginCountry'] = {
                'cbc:IdentificationCode': {'_text': product.l10n_fr_origin_country_id.code}
            }

        # BG-32: AdditionalItemProperty (BT-160, BT-161)
        if 'l10n_fr_item_properties' in line._fields and line.l10n_fr_item_properties:
            item_node['cac:AdditionalItemProperty'] = [
                {
                    'cbc:Name': {'_text': prop.get('name')},
                    'cbc:Value': {'_text': prop.get('value')}
                }
                for prop in line.l10n_fr_item_properties
            ]

    # -------------------------------------------------------------------------
    # IMPORT: French-specific
    # -------------------------------------------------------------------------

    def _is_french_invoice(self, tree):
        """Detect if the invoice is a French CIUS invoice."""

        # Check ProfileID for French billing modes
        profile_id = tree.findtext('./{*}ProfileID')
        if profile_id and profile_id.strip() in FR_BILLING_MODES:
            return True

        # Check for French notes pattern (#PMT#, #PMD#, #AAB#)
        notes = tree.findall('.//{*}Note')
        for note in notes:
            if note.text:
                for code in ('PMT', 'PMD', 'AAB'):
                    if f'#{code}#' in note.text:
                        return True

        # Check seller country
        seller_country = tree.findtext('.//cac:AccountingSupplierParty//cac:Country//cbc:IdentificationCode', namespaces=UBL_NAMESPACES)
        return seller_country and seller_country.strip() == 'FR'

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
        """Import French-specific fields from UBL."""
        logs = []
        invoice_values = {}

        # Import ProfileID as billing mode
        profile_id = tree.findtext('./{*}ProfileID')
        if (
            profile_id
            and profile_id.strip() in FR_BILLING_MODES
            and 'l10n_fr_billing_mode' in invoice._fields
        ):
            invoice_values['l10n_fr_billing_mode'] = profile_id.strip()
            logs.append(f"Mode de facturation français détecté: {profile_id.strip()}")

        # Import French notes with subject codes
        notes_imported = self._import_french_notes(invoice, tree, invoice_values)
        if notes_imported:
            logs.append(f"Notes françaises importées: {', '.join(notes_imported)}")

        # Import SIREN from seller
        siren = self._import_french_siren(tree, 'AccountingSupplierParty')
        if siren:
            logs.append(f"SIREN vendeur détecté: {siren}")

        # Write invoice values if any
        if invoice_values:
            invoice.write(invoice_values)

        return logs

    def _import_french_notes(self, invoice, tree, invoice_values):
        """Parse French notes with subject codes (#CODE#content)."""
        imported_codes = []
        notes = tree.findall('.//{*}Note')

        # Map of codes to field names
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

        for note in notes:
            if not note.text:
                continue

            text = note.text.strip()
            # Parse format: #CODE#Content
            if text.startswith('#') and '#' in text[1:]:
                # Find the second #
                second_hash = text.index('#', 1)
                code = text[1:second_hash]
                content = text[second_hash + 1:]

                if code in code_to_field:
                    field_name = code_to_field[code]
                    if field_name not in invoice._fields:
                        continue
                    invoice_values[field_name] = content
                    imported_codes.append(code)

        return imported_codes

    def _import_french_siren(self, tree, party_role):
        """Extract SIREN from PartyLegalEntity/CompanyID with schemeID='0002'."""

        # Look for CompanyID with schemeID='0002'
        company_ids = tree.findall(f'.//cac:{party_role}//cac:PartyLegalEntity/cbc:CompanyID', namespaces=UBL_NAMESPACES)
        for company_id in company_ids:
            scheme_id = company_id.get('schemeID')
            if scheme_id == '0002' and company_id.text:
                siren = company_id.text.strip()
                # Validate it's a valid SIREN (9 digits)
                if len(siren) == 9 and siren.isdigit():
                    return siren

        return None

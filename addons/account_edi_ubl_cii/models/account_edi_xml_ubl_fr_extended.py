from odoo import models


class AccountEdiXmlUblFrExtended(models.AbstractModel):
    _name = "account.edi.xml.ubl_fr_extended"
    _inherit = "account.edi.xml.ubl_fr"
    _description = "UBL France CIUS Extended"

    # -------------------------------------------------------------------------
    # EXPORT: Configuration
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_fr_extended.xml"

    def _get_customization_ids(self):
        vals = super()._get_customization_ids()
        vals['ubl_fr_extended'] = 'urn:cen.eu:en16931:2017#conformant#urn.cpro.gouv.fr:1p0:extended-ctc-fr'
        return vals

    # -------------------------------------------------------------------------
    # EXPORT: Invoice Header Nodes
    # -------------------------------------------------------------------------

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']

        # Override CustomizationID for Extended profile
        document_node['cbc:CustomizationID'] = {'_text': self._get_customization_ids()['ubl_fr_extended']}

        # Extended ContractDocumentReference with DocumentType
        if 'l10n_fr_contract_reference' in invoice._fields and invoice.l10n_fr_contract_reference:
            contract_ref = document_node.get('cac:ContractDocumentReference', {})
            if 'l10n_fr_contract_document_type' in invoice._fields and invoice.l10n_fr_contract_document_type:
                contract_ref['cbc:DocumentType'] = {'_text': invoice.l10n_fr_contract_document_type}
            document_node['cac:ContractDocumentReference'] = contract_ref

    # -------------------------------------------------------------------------
    # EXPORT: Agent Parties
    # -------------------------------------------------------------------------

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        super()._add_invoice_accounting_supplier_party_nodes(document_node, vals)
        invoice = vals['invoice']

        # Add agent party to AccountingSupplierParty
        supplier_party = document_node.get('cac:AccountingSupplierParty', {}).get('cac:Party', {})
        self._add_agent_party_to_node(supplier_party, invoice, 'supplier')

        # Add ServiceProviderParty to AccountingSupplierParty
        service_provider = self._get_service_provider_party(invoice, 'supplier')
        if service_provider:
            if 'cac:AccountingSupplierParty' not in document_node:
                document_node['cac:AccountingSupplierParty'] = {}
            document_node['cac:AccountingSupplierParty']['cac:ServiceProviderParty'] = service_provider

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        super()._add_invoice_accounting_customer_party_nodes(document_node, vals)
        invoice = vals['invoice']

        # Add agent party to AccountingCustomerParty
        customer_party = document_node.get('cac:AccountingCustomerParty', {}).get('cac:Party', {})
        self._add_agent_party_to_node(customer_party, invoice, 'customer')

        # Add ServiceProviderParty to AccountingCustomerParty
        service_provider = self._get_service_provider_party(invoice, 'customer')
        if service_provider:
            if 'cac:AccountingCustomerParty' not in document_node:
                document_node['cac:AccountingCustomerParty'] = {}
            document_node['cac:AccountingCustomerParty']['cac:ServiceProviderParty'] = service_provider

    def _add_agent_party_to_node(self, party_node, invoice, role):
        """Add AgentParty to the party node if configured."""
        field_name = f'l10n_fr_{role}_agent_id'
        if field_name not in invoice._fields:
            return
        agent = invoice[field_name]
        if not agent:
            return

        party_node['cac:AgentParty'] = self._get_agent_party_node(agent)

    def _get_agent_party_node(self, agent):
        """Build the AgentParty node structure."""
        identifier_scheme = (
            (agent.l10n_fr_identifier_scheme or None)
            if 'l10n_fr_identifier_scheme' in agent._fields
            else None
        )
        peppol_endpoint = (agent.peppol_endpoint or None) if 'peppol_endpoint' in agent._fields else None
        peppol_eas = (agent.peppol_eas or None) if 'peppol_eas' in agent._fields else None

        company_id = None
        siret = (agent.siret or '').strip() if 'siret' in agent._fields and agent.siret else ''
        registry = (agent.company_registry or '').strip() if agent.company_registry else ''
        if len(siret) == 14 and siret.isdigit():
            company_id = {'_text': siret, 'schemeID': '0009'}
        elif len(siret) == 9 and siret.isdigit():
            company_id = {'_text': siret, 'schemeID': '0002'}
        elif len(registry) == 14 and registry.isdigit():
            company_id = {'_text': registry, 'schemeID': '0009'}
        elif len(registry) == 9 and registry.isdigit():
            company_id = {'_text': registry, 'schemeID': '0002'}

        return {
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': agent.name},
                'cbc:CompanyID': company_id,
            },
            'cbc:IndustryClassificationCode': {
                '_text': (
                    agent.industry_id.full_name
                    if 'industry_id' in agent._fields and agent.industry_id
                    else None
                )
            },
            'cac:PartyName': {
                'cbc:Name': {'_text': agent.name}
            },
            'cac:PartyIdentification': {
                'cbc:ID': {
                    '_text': agent.ref,
                    'schemeID': identifier_scheme
                }
            } if agent.ref else None,
            'cac:PartyTaxScheme': {
                'cbc:CompanyID': {'_text': agent.vat},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT'}
                }
            } if agent.vat else None,
            'cbc:EndpointID': {
                '_text': peppol_endpoint,
                'schemeID': peppol_eas
            } if peppol_endpoint and peppol_eas else None,
            'cac:PostalAddress': self._get_address_node({'partner': agent}),
            'cac:Contact': {
                'cbc:Name': {'_text': agent.name},
                'cbc:Telephone': {'_text': agent.phone or agent.mobile},
                'cbc:ElectronicMail': {'_text': agent.email}
            }
        }

    def _get_service_provider_party(self, invoice, role):
        """Get ServiceProviderParty if configured."""
        field_name = f'l10n_fr_{role}_service_provider_id'
        if field_name not in invoice._fields:
            return None
        provider = invoice[field_name]
        if not provider:
            return None

        return {
            'cac:Party': self._get_party_node({
                'partner': provider,
                'role': 'service_provider'
            })
        }

    # -------------------------------------------------------------------------
    # EXPORT: Extended Payee Party
    # -------------------------------------------------------------------------

    def _add_invoice_payee_party_nodes(self, document_node, vals):
        """Add extended PayeeParty with AgentParty structure."""
        invoice = vals['invoice']

        if 'l10n_fr_payee_id' not in invoice._fields or not invoice.l10n_fr_payee_id:
            return

        payee = invoice.l10n_fr_payee_id
        document_node['cac:PayeeParty'] = {
            'cac:PartyName': {
                'cbc:Name': {'_text': payee.name}
            },
            # Extended: use full AgentParty structure
            **self._get_agent_party_node(payee)
        }

    # -------------------------------------------------------------------------
    # EXPORT: Extended Payment Means with PayerParty
    # -------------------------------------------------------------------------

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        super()._add_invoice_payment_means_nodes(document_node, vals)
        invoice = vals['invoice']

        payment_means = document_node.get('cac:PaymentMeans', {})

        # Extended: PayerParty
        if 'l10n_fr_payer_party_id' in invoice._fields and invoice.l10n_fr_payer_party_id:
            payer = invoice.l10n_fr_payer_party_id
            payment_means['cac:PayerParty'] = self._get_agent_party_node(payer)

    # -------------------------------------------------------------------------
    # EXPORT: Extended Invoice Line
    # -------------------------------------------------------------------------

    def _get_invoice_line_node(self, vals):
        line_node = super()._get_invoice_line_node(vals)
        base_line = vals['base_line']
        line = base_line.get('record')

        if not line:
            return line_node

        # Extended: Multiple DocumentReferences
        if 'l10n_fr_document_references' in line._fields and line.l10n_fr_document_references:
            line_node['cac:DocumentReference'] = [
                {
                    'cbc:ID': {
                        '_text': ref.get('id'),
                        'schemeID': ref.get('scheme_id')
                    }
                }
                for ref in line.l10n_fr_document_references
            ]

        # Extended: BillingReference
        if 'l10n_fr_billing_reference_id' in line._fields and line.l10n_fr_billing_reference_id:
            billing_ref = line.l10n_fr_billing_reference_id
            line_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': billing_ref},
                    'cbc:IssueDate': {
                        '_text': line.l10n_fr_billing_reference_date or None
                        if 'l10n_fr_billing_reference_date' in line._fields
                        else None
                    },
                    'cbc:DocumentTypeCode': {
                        '_text': line.l10n_fr_billing_reference_type or None
                        if 'l10n_fr_billing_reference_type' in line._fields
                        else None
                    }
                }
            }

        # Extended: DespatchLineReference
        if 'l10n_fr_despatch_line_id' in line._fields and line.l10n_fr_despatch_line_id:
            line_node['cac:DespatchLineReference'] = {
                'cac:DocumentReference': {
                    'cbc:ID': {
                        '_text': line.l10n_fr_despatch_doc_id or None
                        if 'l10n_fr_despatch_doc_id' in line._fields
                        else None
                    }
                },
                'cbc:LineID': {'_text': line.l10n_fr_despatch_line_id}
            }

        # Extended: ReceiptLineReference
        if 'l10n_fr_receipt_line_id' in line._fields and line.l10n_fr_receipt_line_id:
            line_node['cac:ReceiptLineReference'] = {
                'cac:DocumentReference': {
                    'cbc:ID': {
                        '_text': line.l10n_fr_receipt_doc_id or None
                        if 'l10n_fr_receipt_doc_id' in line._fields
                        else None
                    }
                },
                'cbc:LineID': {'_text': line.l10n_fr_receipt_line_id}
            }

        # Extended: OrderLineReference with OrderReference and SalesOrderLineID
        if 'l10n_fr_sales_order_line_id' in line._fields and line.l10n_fr_sales_order_line_id:
            order_line_ref = line_node.get('cac:OrderLineReference', {})
            order_line_ref['cac:OrderReference'] = {
                'cbc:ID': {
                    '_text': line.l10n_fr_order_id or None
                    if 'l10n_fr_order_id' in line._fields
                    else None
                },
                'cbc:SalesOrderID': {
                    '_text': line.l10n_fr_sales_order_id or None
                    if 'l10n_fr_sales_order_id' in line._fields
                    else None
                }
            }
            order_line_ref['cbc:SalesOrderLineID'] = {'_text': line.l10n_fr_sales_order_line_id}
            line_node['cac:OrderLineReference'] = order_line_ref

        return line_node

    # -------------------------------------------------------------------------
    # EXPORT: Extended Delivery
    # -------------------------------------------------------------------------

    def _add_invoice_delivery_nodes(self, document_node, vals):
        super()._add_invoice_delivery_nodes(document_node, vals)
        invoice = vals['invoice']

        delivery_node = document_node.get('cac:Delivery', {})

        # Extended: Multiple DeliveryLocations with IDs
        if 'l10n_fr_delivery_locations' in invoice._fields and invoice.l10n_fr_delivery_locations:
            delivery_node['cac:DeliveryLocation'] = [
                {
                    'cbc:ID': {
                        '_text': loc.get('id'),
                        'schemeID': loc.get('scheme_id')
                    }
                }
                for loc in invoice.l10n_fr_delivery_locations
            ]

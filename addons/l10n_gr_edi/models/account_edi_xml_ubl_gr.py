from datetime import datetime

from odoo import models
from odoo.exceptions import ValidationError


class AccountEdiXmlUblGr(models.AbstractModel):
    _name = 'account.edi.xml.ubl_gr'
    _inherit = 'account.edi.xml.ubl_bis3'
    _description = "Greek PEPPOL CIUS for B2G invoicing based on UBL BIS 3.0"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_gr_peppol_cius.xml"

    def _is_greek_supplier(self, invoice):
        return invoice.company_id.country_id.code == 'GR'

    def _is_greek_b2g_invoice(self, invoice):
        return invoice.l10n_gr_edi_state == 'invoice_sent'

    def _get_greek_vat_number(self, invoice):
        if invoice.company_id.l10n_gr_edi_has_tax_representative:
            vat_number = invoice.company_id.l10n_gr_edi_tax_representative_partner_id.vat
        else:
            vat_number = invoice.company_id.vat
        return vat_number

    def _format_greek_invoice_number(self, invoice):
        # GR-R-001-2: First segment - VAT without EL prefix
        company_vat = self._get_greek_vat_number(invoice)
        if company_vat.startswith('EL'):
            company_vat = company_vat[2:]
        # GR-R-001-3: Second segment - Issue date DD/MM/YYYY
        issue_date = invoice.invoice_date.strftime('%d/%m/%Y')
        # GR-R-001-4: Third segment - Installation serial(branch number)
        installation_sn = str(invoice.company_id.l10n_gr_edi_branch_number)
        # GR-R-001-5: Fourth segment - Valid Greek document type
        invoice_type = invoice.l10n_gr_edi_inv_type
        # GR-R-001-6: Fifth segment - Series
        series = invoice.name.split('/')[0]
        # GR-R-001-7: Sixth segment - Serial number
        serial_number = invoice.name.split('/')[-1]
        return f"{company_vat}|{issue_date}|{installation_sn}|{invoice_type}|{series}|{serial_number}"

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        document_node.update({
            # BT-1: Invoice number with format: "VAT|Issue date|Installation sn.|Invoice Type|Series|eINV Issue sn."
            'cbc:ID': {'_text': self._format_greek_invoice_number(invoice)},
            # BT-10: Buyer reference - Contracting authority name
            'cbc:BuyerReference': {'_text': invoice.partner_id.l10n_gr_edi_contracting_authority_name},
        })

    # -------------------------------------------------------------------------
    # EXPORT VALUES
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)
        invoice = vals['invoice']
        if vals['document_type'] != 'credit_note':
            # BT-11: ProjectReference
            if invoice.l10n_gr_edi_budget_type and invoice.l10n_gr_edi_project_reference:
                document_node['cac:ProjectReference'] = {
                    'cbc:ID': {'_text': f"{invoice.l10n_gr_edi_budget_type}|{invoice.l10n_gr_edi_project_reference}"}
                }
            # BT-12: ContractDocumentReference
            if invoice.l10n_gr_edi_contract_reference:
                document_node['cac:ContractDocumentReference'] = {
                    'cbc:ID': {'_text': invoice.l10n_gr_edi_contract_reference}
                }
            # BT-122 AdditionalDocumentReference (M.AR.K)
            if self._is_greek_supplier(invoice) and invoice.l10n_gr_edi_mark:
                document_node['cac:AdditionalDocumentReference'] = [{
                    'cbc:ID': {'_text': str(invoice.l10n_gr_edi_mark)},
                    'cbc:DocumentTypeCode': {'_text': '130'},
                    'cbc:DocumentDescription': {'_text': '##M.AR.K##'},
                }]
        # BillingReference
        elif vals['document_type'] == 'credit_note':
            if invoice.reversed_entry_id:
                document_node['cac:BillingReference'] = {
                    'cac:InvoiceDocumentReference': {
                        'cbc:ID': {'_text': self._format_greek_invoice_number(invoice.reversed_entry_id)},
                    }
                }
        return document_node

    # -------------------------------------------------------------------------
    # Party Nodes (Supplier & Customer)
    # -------------------------------------------------------------------------

    def _get_party_node(self, vals):
        """EXTENDS account.edi.xml.ubl_bis3"""
        party_node = super()._get_party_node(vals)
        partner = vals['partner']
        if vals['role'] == 'supplier':
            # Tax representative(GR-R-007)
            # Note: TaxRepresentativeParty is not in the current UBL template.
            # When template is updated to support it, uncomment the code below:
            # if vals['company'].l10n_gr_edi_has_tax_representative and vals['document_type'] != 'credit_note':
            #     tax_rep = vals['company'].l10n_gr_edi_tax_representative_partner_id
            #     self._add_tax_representative_node(party_node, tax_rep)
            pass
        elif vals['role'] == 'customer':
            # BT-46: Contracting authority code (HT code for Greek contracting authorities)
            if partner.l10n_gr_edi_contracting_authority_code:
                party_node['cac:PartyIdentification'].update({
                    'cbc:ID': {'_text': partner.l10n_gr_edi_contracting_authority_code}
                })
        return party_node

    def _add_tax_representative_node(self, party_node, tax_rep):
        party_node['cac:TaxRepresentativeParty'] = {
            # BT-62: Tax representative name
            'cac:PartyName': {
                'cbc:Name': {'_text': tax_rep.name}
            },
            # BT-63: Tax representative VAT
            'cac:PartyTaxScheme': {
                'cbc:CompanyID': {'_text': tax_rep.vat},
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT'}
                }
            }
        }

    # -------------------------------------------------------------------------
    # Line Item Nodes
    # -------------------------------------------------------------------------

    def _add_invoice_line_item_nodes(self, line_node, vals):
        """ EXTENDS account.edi.xml.ubl_bis3
            BT-158 CPV (Common Procurement Vocabulary) code
        """
        super()._add_invoice_line_item_nodes(line_node, vals)
        line = vals['base_line']['record']
        if line and line.product_id:
            cpv_code = line.product_id.l10n_gr_edi_cpv_code
            if cpv_code:
                if 'cac:Item' not in line_node:
                    line_node['cac:Item'] = {}
                if 'cac:CommodityClassification' not in line_node['cac:Item']:
                    line_node['cac:Item']['cac:CommodityClassification'] = []
                line_node['cac:Item']['cac:CommodityClassification'].append({
                    'cbc:ItemClassificationCode': {
                        '_text': cpv_code,
                        'listID': 'CPV'
                    }
                })

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals) or {}
        if not self._is_greek_b2g_invoice(invoice):
            constraints['gr_b2g_check'] = self.env._(
                "This invoice cannot be processed for Greek B2G invoicing via PEPPOL. Please deselect peppol as invoice sending method."
            )
        else:
            constraints.update(self._validate_greek_business_rules(invoice))
        return constraints

    def _validate_greek_business_rules(self, invoice):
        """Comprehensive validation of all Greek PEPPOL CIUS business rules"""
        constraints = {}
        # GR-R-001: Invoice number format validation
        try:
            formatted_number = self._format_greek_invoice_number(invoice)
            segments = formatted_number.split('|')
            # GR-R-001-1: Must have 6 segments
            if len(segments) != 6:
                constraints['gr_r_001_1'] = self.env._("Greek invoice number must have 6 segments")
            # GR-R-001-2: First segment TIN validation
            if not segments[0]:
                constraints['gr_r_001_2'] = self.env._("First segment must be valid Greek TIN")
            # GR-R-001-3: Date validation
            try:
                segment_date = datetime.strptime(segments[1], '%d/%m/%Y').date()
                if segment_date != invoice.invoice_date:
                    constraints['gr_r_001_3'] = self.env._("Invoice date in number must match issue date")
            except ValueError:
                constraints['gr_r_001_3'] = self.env._("Invalid date format in invoice number")
            # GR-R-001-5: Fourth segment - Valid Greek document type
            if not invoice.l10n_gr_edi_inv_type:
                constraints['gr_r_001_5'] = self.env._("Missing Greek Invoice type")
        except ValidationError as e:
            constraints['gr_r_001_format'] = str(e)
        # GR-R-003: Supplier VAT validation
        if not invoice.company_id.vat.startswith('EL'):
            constraints['gr_r_003'] = self.env._("Greek supplier VAT must start with 'EL'")
        # GR-R-004: M.AR.K validation
        if not invoice.l10n_gr_edi_mark:
            constraints['gr_r_004_1'] = self.env._("M.AR.K number is required for Greek suppliers")
        else:
            if int(invoice.l10n_gr_edi_mark) <= 0:
                constraints['gr_r_004_2'] = self.env._("M.AR.K must be positive integer")
        # GR-R-006: Greek buyer VAT validation
        if invoice.partner_id.country_id.code == 'GR':
            buyer_vat = invoice.partner_id.commercial_partner_id.vat
            if not buyer_vat or not buyer_vat.startswith('EL'):
                constraints['gr_r_006'] = self.env._("Greek buyer VAT must start with prefix 'EL'")
        # GR-R-007: Project reference validation
        if not invoice.l10n_gr_edi_budget_type and not invoice.l10n_gr_edi_project_reference:
            constraints['gr_r_007'] = self.env._("Budget Type and Project reference (ADA or Enaritmos number) is required for B2G invoicing")
        # GR-R-008: Contract reference validation
        if not invoice.l10n_gr_edi_contract_reference:
            constraints['gr_r_008'] = self.env._("Contract reference (ADAM number) is required for this invoice type")
        return constraints

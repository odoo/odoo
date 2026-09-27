from stdnum.gr import vat

from odoo import models


class AccountEdiXmlUblGr(models.AbstractModel):
    _name = 'account.edi.xml.ubl_gr'
    _inherit = 'account.edi.xml.ubl_bis3'
    _description = "CIUS GR"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_gr_peppol_cius.xml"

    def _format_greek_invoice_number(self, invoice):
        # GR-R-001-2: First segment - VAT without EL prefix
        company_vat = vat.compact(invoice.company_id.vat or '')
        invoice_name = invoice.name.split('/')
        # GR-R-001-3: Second segment - Issue date DD/MM/YYYY
        issue_date = invoice.invoice_date.strftime('%d/%m/%Y')
        # GR-R-001-4: Third segment - Installation serial(branch number)
        installation_sn = str(invoice.company_id.l10n_gr_edi_branch_number)
        # GR-R-001-5: Fourth segment - Valid Greek document type
        invoice_type = invoice.l10n_gr_edi_inv_type
        # GR-R-001-6: Fifth segment - Series
        series = invoice_name[0]
        # GR-R-001-7: Sixth segment - Serial number
        serial_number = invoice_name[-1]
        return f"{company_vat}|{issue_date}|{installation_sn}|{invoice_type}|{series}|{serial_number}"

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        document_node.update({
            # BT-1: Invoice number with format: "VAT|Issue date|Installation sn.|Invoice Type|Series|eINV Issue sn."
            'cbc:ID': {'_text': self._format_greek_invoice_number(invoice)},
        })
        # BT-10: Buyer reference - Contracting authority name
        buyer = invoice.partner_id.commercial_partner_id
        if buyer.l10n_gr_edi_contracting_authority_name:
            document_node['cbc:BuyerReference'] = {'_text': buyer.l10n_gr_edi_contracting_authority_name}

    # -------------------------------------------------------------------------
    # EXPORT VALUES
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)
        invoice = vals['invoice']
        additional_document_references = document_node.setdefault('cac:AdditionalDocumentReference', [])
        if not isinstance(additional_document_references, list):
            additional_document_references = [additional_document_references]
            document_node['cac:AdditionalDocumentReference'] = additional_document_references
        additional_document_references.append({
            'cbc:ID': {'_text': str(invoice.l10n_gr_edi_mark)},
            'cbc:DocumentDescription': {'_text': '##M.AR.K##'},
        })

        if vals['document_type'] != 'credit_note':
            # BT-11: ProjectReference
            document_node['cac:ProjectReference'] = {
                'cbc:ID': {'_text': f"{invoice.l10n_gr_edi_budget_type}|{invoice.l10n_gr_edi_project_reference}"}
            }
            # BT-12: ContractDocumentReference
            document_node['cac:ContractDocumentReference'] = {
                'cbc:ID': {'_text': invoice.l10n_gr_edi_contract_reference}
            }
        # BT-25 Billing reference (preceding invoice number) for credit notes
        elif vals['document_type'] == 'credit_note':
            reversed_entry = invoice.reversed_entry_id
            document_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': self._format_greek_invoice_number(reversed_entry) if reversed_entry else ''},
                }
            }
        return document_node

    # -------------------------------------------------------------------------
    # Party Nodes (Supplier & Customer)
    # -------------------------------------------------------------------------

    def _ubl_add_party_endpoint_id_node(self, vals):
        super()._ubl_add_party_endpoint_id_node(vals)
        party_node = vals['party_node']
        endpoint_node = party_node.get('cbc:EndpointID')
        if endpoint_node and endpoint_node.get('schemeID') == '9933':
            endpoint_node['_text'] = vat.compact(endpoint_node.get('_text') or '')

    def _ubl_add_party_identification_nodes(self, vals):
        super()._ubl_add_party_identification_nodes(vals)
        partner = vals['party_vals']['partner']
        buyer = vals['customer'].commercial_partner_id
        # BT-46: Contracting authority code (HT code for Greek contracting authorities)
        if partner.id == vals['customer'].id and buyer.l10n_gr_edi_contracting_authority_code:
            nodes = vals['party_node'].setdefault('cac:PartyIdentification', [])
            nodes.append({
                'cbc:ID': {'_text': buyer.l10n_gr_edi_contracting_authority_code}
            })

    # -------------------------------------------------------------------------
    # Line Item Nodes
    # -------------------------------------------------------------------------

    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)
        line = vals['base_line']['record']
        # BT-158 CPV (Common Procurement Vocabulary) code
        if not line or not line.l10n_gr_edi_cpv_code:
            return
        item = line_node.setdefault('cac:Item', {})
        commodity_node = item.setdefault('cac:CommodityClassification', [])
        commodity_node.append({
            'cbc:ItemClassificationCode': {
                '_text': line.l10n_gr_edi_cpv_code,
                'listID': 'STI'
            }
        })

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals) or {}
        constraints.update(self._validate_greek_business_rules(invoice))
        return constraints

    def _validate_greek_business_rules(self, invoice):
        """Validation of all Greek PEPPOL CIUS business rules"""
        constraints = {}
        supplier_vat = invoice.company_id.vat or ''
        buyer = invoice.partner_id.commercial_partner_id
        buyer_vat = buyer.vat or ''
        _ = self.env._
        # check format : (code, condition, error message)
        checks = [
            ('gr_r_001_5', not invoice.l10n_gr_edi_inv_type, _("Missing Greek Invoice type")),
            ('gr_r_003', not supplier_vat.upper().startswith('EL'), _("Supplier VAT must start with 'EL'")),
            ('gr_r_004_1', not invoice.l10n_gr_edi_mark, _("M.AR.K number is required for Suppliers")),
            ('gr_r_006', not buyer_vat or not buyer_vat.upper().startswith('EL'), _("Buyer VAT must start with prefix 'EL'")),
            ('gr_bt_10', not buyer.l10n_gr_edi_contracting_authority_name, _("Contracting authority name is required for Greek buyer")),
            ('gr_bt_46', not buyer.l10n_gr_edi_contracting_authority_code, _("Contracting authority code is required for Greek buyer")),
            ('gr_r_007', invoice.move_type != 'out_refund' and not (invoice.l10n_gr_edi_budget_type and invoice.l10n_gr_edi_project_reference), _("Budget Type and Project reference is required for B2G invoicing")),
            ('gr_bt_25', invoice.move_type == 'out_refund' and not invoice.reversed_entry_id, _("A Greek CIUS credit note must reference the original invoice.")),
        ]
        for code, condition, message in checks:
            if condition:
                constraints[code] = message
        # BT-158: CPV code (KED mandatory fields)
        for line in invoice.invoice_line_ids:
            if line.product_id and not line.l10n_gr_edi_cpv_code:
                constraints['gr_bt_158'] = _(
                    "Each invoice line with a product must have a CPV code for Greek B2G invoicing."
                    "Set CPV code on the product or on the line."
                )
                break
        return constraints

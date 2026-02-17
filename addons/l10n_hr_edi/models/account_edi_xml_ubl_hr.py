# UBL structure for CIUS HR
# Updated to work with but doesn't entirely follow the full structure of the UBL rework
# implemented in commit a3c6e5abe0d964f0768de68d526905ae3dccac8a

from odoo import fields, models
from odoo.tools import html2plaintext
from lxml import etree


class AccountEdiXmlUBLHR(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'
    _name = 'account.edi.xml.ubl_hr'
    _description = "CIUS HR"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_hr.xml"

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _get_document_template(self, vals):
        ext_template = {
            'ext:UBLExtension': {
                'ext:ExtensionContent': {
                    'hrextac:HRFISK20Data': {
                        'hrextac:HRObracunPDVPoNaplati': {},
                        'hrextac:HRTaxTotal': {
                            'cbc:TaxAmount': {},
                            'hrextac:HRTaxSubtotal': {
                                'cbc:TaxableAmount': {},
                                'cbc:TaxAmount': {},
                                'hrextac:HRTaxCategory': {
                                    'cbc:ID': {},
                                    'cbc:Name': {},
                                    'cbc:Percent': {},
                                    'cbc:TaxExemptionReasonCode': {},
                                    'cbc:TaxExemptionReason': {},
                                    'hrextac:HRTaxScheme': {
                                        'cbc:ID': {},
                                    }
                                }
                            }
                        },
                        'hrextac:HRLegalMonetaryTotal': {
                            'cbc:TaxExclusiveAmount': {},
                            'hrextac:OutOfScopeOfVATAmount': {},
                        }
                    }
                }
            }
        }
        template = super()._get_document_template(vals)
        # Overriding the node as it appears to be localization-specific
        template['ext:UBLExtensions'] = ext_template
        return template

    def _get_document_nsmap(self, vals):
        nsmap = super()._get_document_nsmap(vals)
        nsmap.update({
            'hrextac': "urn:mfin.gov.hr:schema:xsd:HRExtensionAggregateComponents-1",
        })
        return nsmap

    def _export_invoice_constraints(self, invoice, vals):
        # OVERRIDE 'account.edi.xml.ubl_bis3': don't apply Peppol rules
        constraints = self.env['account.edi.xml.ubl_20']._export_invoice_constraints(invoice, vals)
        constraints.update(
            self._invoice_constraints_cen_en16931_ubl(invoice, vals)
        )
        constraints.update(
            self._invoice_constraints_eracun_new(invoice, vals)
        )
        return constraints

    def _invoice_constraints_eracun_new(self, invoice, vals):
        # Corresponds to Croatian eRacun format constrains
        constraints = {}
        if vals['document_type'] in ['invoice', 'credit_note']:
            if any(c.isspace() for c in vals['document_node']['cac:PaymentMeans']['cac:PayeeFinancialAccount']['cbc:ID'].get('_text')):
                constraints.update({'ubl_hr_br_1': self.env._("HR-BR-1: The account number must not contain whitespace characters.")})
            if invoice.amount_residual > 0 and not invoice.invoice_date_due:
                constraints.update({'ubl_hr_br_4': self.env._("HR-BT-4: In the case of a positive amount due for payment (BT-115), the payment due date (BT-9) must be specified.")})
            constraints.update({
                'ubl_hr_br_7_seller_email_required': (
                    self.env._("The Seller's e-mail must be provided.")
                ) if not vals['document_node']['cac:AccountingSupplierParty']['cac:Party']['cac:Contact']['cbc:ElectronicMail'].get('_text') else None,
                'ubl_hr_br_10_buyer_email_required': (
                    self.env._("The Buyer's e-mail must be provided.")
                ) if not vals['document_node']['cac:AccountingCustomerParty']['cac:Party']['cac:Contact']['cbc:ElectronicMail'].get('_text') else None,
                'ubl_hr_br_s_buyer_vat_required': (
                    self.env._("The invoice must contain the Customer's VAT identification number (BT-48).")
                ) if any(not item['cbc:CompanyID'].get('_text') for item in vals['document_node']['cac:AccountingCustomerParty']['cac:Party']['cac:PartyTaxScheme']) else None,
                'ubl_hr_br_37_operator_label_required': (
                    self.env._("The invoice must contain the Operator Label (HR-BT-4).")
                ) if not vals['document_node']['cac:AccountingSupplierParty']['cac:SellerContact']['cbc:Name'].get('_text') else None,
                'ubl_hr_br_9_operator_oib_required': (
                    self.env._("The invoice must contain the Operator OIB (HR-BT-5).")
                ) if not vals['document_node']['cac:AccountingSupplierParty']['cac:SellerContact']['cbc:ID'].get('_text') else None,
            })
        return constraints

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)
        # HRFISC20Data extension support
        self._add_hr_extension_node(document_node)
        return document_node

    def _add_invoice_header_nodes(self, document_node, vals):
        super()._add_invoice_header_nodes(document_node, vals)
        invoice = vals['invoice']
        document_node.update({
            # For Croatia, ID should be the Croatian-format fiscalization number
            'cbc:ID': {
                '_text': invoice.l10n_hr_fiscalization_number
            },
            # HR-BT-1: Copy indicator - is the invoice the original or already sent
            #   This doesn't appear to be currently supported in Odoo, and is set to 'false' in TR localization using a similar format
            'cbc:CopyIndicator': {
                    '_text': 'false'
            },
            # HR-BT-2: The invoice must have an invoice issuance time.
            #   (in addition to BT-2: Date of issue)
            'cbc:IssueDate': {
                '_text': fields.Datetime.to_string(invoice.l10n_hr_invoice_sending_time).split()[0]
            },
            'cbc:IssueTime': {
                '_text': fields.Datetime.to_string(invoice.l10n_hr_invoice_sending_time).split()[1]
            },
            # HR-BR-34: The process label MUST be specified. Values P1-P12 or P99:Customer ID from Table 4 Business Process Types are used.
            'cbc:ProfileID': {
                '_text': f"P99:{invoice.l10n_hr_customer_defined_process_name}" if invoice.l10n_hr_process_type == 'P99' else invoice.l10n_hr_process_type
            },
            # HR-BR-5: The specification identifier must have the value
            # 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0'
            'cbc:CustomizationID': {
                '_text': 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0'
            },
        })
        # HR-BT-4: In the case of a positive amount due for payment (BT-115), the payment due date (BT-9) must be specified.
        if invoice.amount_residual > 0 and not document_node['cbc:DueDate'] and vals['document_type'] == 'invoice':
            if invoice.invoice_date_due:
                document_node.update({
                    'cbc:DueDate': {
                        '_text': invoice.invoice_date_due
                    }
                })
        # HR-BT-3: Note on previous invoice
        # HR-BR-6: Each previous invoice reference (BG-3) must have the date of issue of the previous invoice (BT-26).
        if 'refund' in invoice.move_type and invoice.reversed_entry_id:
            document_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': invoice.ref},
                },
                'cbc:IssueDate': {
                    '_text': invoice.reversed_entry_id.invoice_date
                }
            }
        # Document Type Codes and Process Type Logic
        if invoice.l10n_hr_process_type in ('P4', 'P6'):
            if invoice.move_type == 'out_invoice':
                document_node['cbc:InvoiceTypeCode'].update({
                    '_text': '386'
                })
            elif invoice.move_type == 'out_refund':
                document_node['cbc:CreditNoteTypeCode'].update({
                    '_text': '386'
                })
        elif invoice.l10n_hr_process_type == 'P9':
            document_node['cbc:CreditNoteTypeCode'].update({
                '_text': '381'
            })

    def _add_hr_extension_node(self, document_node):
        """
        This function constructs hrextac node from existing data within the document.
        The structure mostly follows that of 'cac:TaxTotal' node of a UBL 2.1/BIS 3 document,
        but requires additional data compared to the totals/subtotals nodes in UBL HR format.
        To avoid making additional queries and possible desyncs, we calculate all the data
        we need while assembling normal subtotals, then trim out the extra bits.
        """
        cash_basis_line = False
        tax_totals = document_node['cac:TaxTotal']
        hr_tax_totals = []
        for total in tax_totals:
            tax_subtotals = total['cac:TaxSubtotal']
            hr_tax_subtotals = []
            for subtotal in tax_subtotals:
                tax_categories = subtotal['cac:TaxCategory']
                hr_tax_categories = []
                for category in tax_categories:
                    # Cash basis is document-wide, so we do not need to keep it for each category
                    cash_basis_flag = category.pop('hrextac:HRObracunPDVPoNaplati')  # Ensure pop() always runs
                    cash_basis_line = cash_basis_line or cash_basis_flag
                    # Removing the HR-specific node from the normal subtotal where we calculate it
                    hr_tax_name = category.pop('cbc:Name')
                    hr_tax_categories.append({
                        'cbc:ID': category['cbc:ID'],
                        'cbc:Name': hr_tax_name,
                        'cbc:Percent': category['cbc:Percent'],
                        'cbc:TaxExemptionReasonCode': category['cbc:TaxExemptionReasonCode'],
                        'cbc:TaxExemptionReason': category['cbc:TaxExemptionReason'],
                        'hrextac:HRTaxScheme': category['cac:TaxScheme'] if hr_tax_name['_text'] != "HR:POVNAK" else {'_text': "OTH"},
                    })
                hr_tax_subtotals.append({
                    'cbc:TaxableAmount': subtotal['cbc:TaxableAmount'],
                    'cbc:TaxAmount': subtotal['cbc:TaxAmount'],
                    'hrextac:HRTaxCategory': hr_tax_categories.copy(),
                })
            hr_tax_totals.append({
                'cbc:TaxAmount': total['cbc:TaxAmount'],
                'hrextac:HRTaxSubtotal': hr_tax_subtotals.copy(),
            })
        out_of_scope_node = {
            'currencyID': document_node['cac:LegalMonetaryTotal']['cbc:TaxExclusiveAmount'].get('currencyID'),
            '_text': '0.00'     # Currently unsupported, a HR-specific workaround can potentially be made
        }
        document_node.update({
            'ext:UBLExtensions': {
                'ext:UBLExtension': {
                    'ext:ExtensionContent': {
                        'hrextac:HRFISK20Data': {
                            'hrextac:HRObracunPDVPoNaplati': cash_basis_line,
                            'hrextac:HRTaxTotal': hr_tax_totals,
                            'hrextac:HRLegalMonetaryTotal': {
                                'cbc:TaxExclusiveAmount': document_node['cac:LegalMonetaryTotal']['cbc:TaxExclusiveAmount'],
                                'hrextac:OutOfScopeOfVATAmount': out_of_scope_node,
                            }
                        }
                    },
                }
            }
        })

    def _add_invoice_line_item_nodes(self, line_node, vals):
        super()._add_invoice_line_item_nodes(line_node, vals)
        # HR-BR-25: Each item MUST have an item classification identifier from the Classification of Products
        # by Activities scheme: KPD (CPA) - listID "CG", except in the case of advance payment invoices.
        line = vals['base_line']['record']
        line_node['cac:Item'].update({
            'cac:CommodityClassification': {
                'cbc:ItemClassificationCode': {
                    'listID': 'CG',
                    '_text': line.l10n_hr_kpd_category_id.name
                }
            }
        })

    def _ubl_add_party_identification_nodes(self, vals):
        # EXTENDS account.edi.ubl_bis3
        super()._ubl_add_party_identification_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        if commercial_partner.l10n_hr_personal_oib:
            if commercial_partner.l10n_hr_business_unit_code:
                vals['party_node']['cac:PartyIdentification'] = [{
                    'cbc:ID': {
                        '_text': f'9934:{commercial_partner.l10n_hr_personal_oib}::HR99:{commercial_partner.l10n_hr_business_unit_code}',
                        'schemeID': None,
                    },
                }]
            else:
                vals['party_node']['cac:PartyIdentification'] = [{
                    'cbc:ID': {
                        '_text': f'9934:{commercial_partner.l10n_hr_personal_oib}',
                        'schemeID': None,
                    },
                }]
        elif commercial_partner.company_registry:
            vals['party_node']['cac:PartyIdentification'] = [{
                'cbc:ID': {
                    '_text': f'0088:{commercial_partner.company_registry}',
                    'schemeID': None,
                },
            }]

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        super()._add_invoice_accounting_supplier_party_nodes(document_node, vals)
        # HR-BR-37: Invoice must contain HR-BT-4: Operator code in accordance with the Fiscalization Act.
        # HR-BR-9: Invoice must contain HR-BT-5: Operator OIB in accordance with the Fiscalization Act.
        invoice = vals['invoice']
        document_node['cac:AccountingSupplierParty'].update({
            'cac:SellerContact': {
                'cbc:ID': {
                    '_text': invoice.l10n_hr_operator_oib
                },
                'cbc:Name': {
                    '_text': invoice.l10n_hr_operator_name
                }
            }
        })

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # EXTENDS account.edi.xml.ubl_bis3
        grouping_key = super()._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency)
        if not grouping_key or not tax_data:
            return

        tax = tax_data['tax']
        hr_category = tax.l10n_hr_tax_category_id if tax else None

        # HR-BR-11: Each document-level expense (BG-21) that is not subject to VAT or is exempt from VAT must have
        # a document-level expense VAT category code (HR-BT-6) from table HR-TB-2 HR VAT category codes
        #   Instead of determining what the elements should be from the invoice details, here we directly use
        #   the data of the VAT expence category defined on the tax by the user
        if (
            tax.l10n_hr_tax_category_id
            and tax.amount_type == 'percent'
            and not tax.amount
        ):
            grouping_key.update({
                'tax_category_code': tax.l10n_hr_tax_category_id.code_untdid
            })
            # If account_edi_ubl_cii_tax_extension is installed and a value is specified, use that data, if not, override with HR data
            tax_extension = 'ubl_cii_tax_exemption_reason_code' in tax._fields and tax.ubl_cii_tax_exemption_reason_code
            if not tax_extension:
                grouping_key.update({'tax_exemption_reason': hr_category.description})

        if tax.tax_exigibility == 'on_payment':
            invoice_legal_notes_str = html2plaintext(tax.invoice_legal_notes or '') or "Obračun po naplaćenoj naknadi"
        else:
            invoice_legal_notes_str = None

        grouping_key.update({
            'hr_category_name': tax.l10n_hr_tax_category_id.name,
            'invoice_legal_notes_str': invoice_legal_notes_str,
        })
        return grouping_key

    def _ubl_get_tax_category_node(self, vals, tax_category):
        # EXTENDS account.edi.xml.ubl_bis3
        node = super()._ubl_get_tax_category_node(vals, tax_category)
        node['cbc:Name']['_text'] = tax_category['hr_category_name']
        node['hrextac:HRObracunPDVPoNaplati'] = {'_text': tax_category['invoice_legal_notes_str']}
        return node

    def _ubl_get_line_item_node_classified_tax_category_node(self, vals, tax_category):
        # EXTENDS account.edi.xml.ubl_bis3
        node = super()._ubl_get_line_item_node_classified_tax_category_node(vals, tax_category)
        node['cbc:Name']['_text'] = tax_category['hr_category_name']
        node['cbc:TaxExemptionReasonCode']['_text'] = tax_category.get('tax_exemption_reason_code')
        node['cbc:TaxExemptionReason']['_text'] = tax_category.get('tax_exemption_reason')
        return node

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        logs = super()._import_fill_invoice(invoice, tree, qty_factor)
        profile_id = tree.findtext('./{*}ProfileID')
        invoice_values = {
            'l10n_hr_process_type': profile_id[:3] if profile_id[:3] == 'P99' else profile_id,
            'l10n_hr_customer_defined_process_name': profile_id[4:] if profile_id[:3] == 'P99' else False,
        }
        invoice.write(invoice_values)
        invoice.l10n_hr_edi_addendum_id.write({'fiscalization_number': tree.findtext('./{*}ID')})
        return logs

    def _import_invoice_lines(self, invoice, tree, xpath, qty_factor):
        # Override to work with Croatian tax exigibility flag
        tax_exigibility = 'on_payment' if tree.find('.//{*}HRObracunPDVPoNaplati') is not None else 'on_invoice'
        logs = []
        lines_values = []
        for line_tree in tree.iterfind(xpath):
            line_values = self.with_company(invoice.company_id)._retrieve_invoice_line_vals(line_tree, invoice.move_type, qty_factor)
            if line_values is None:
                continue

            line_values['tax_ids'], tax_logs = self._retrieve_taxes(
                invoice, line_values, invoice.journal_id.type, tax_exigibility,
            )
            logs += tax_logs
            if not line_values['product_uom_id']:
                line_values.pop('product_uom_id')  # if no uom, pop it so it's inferred from the product_id
            lines_values.append(line_values)
            lines_values += self._retrieve_line_charges(invoice, line_values, line_values['tax_ids'])
        return lines_values, logs

    def _retrieve_line_vals(self, tree, document_type=False, qty_factor=1):
        line_values = super()._retrieve_line_vals(tree, document_type, qty_factor)
        kpd_category_code = tree.findtext('./{*}Item/{*}CommodityClassification/{*}ItemClassificationCode')
        if kpd_category_code:
            line_kpd_category = self.env['l10n_hr.kpd.category'].search([('name', '=', kpd_category_code)], limit=1)
            if line_kpd_category:
                line_values.update({
                    'l10n_hr_kpd_category_id': line_kpd_category.id,
                })
        return line_values

    def _retrieve_rejection_reference(self, attachment):
        string_to_find = b'Rejected</cbc:StatusReasonCode>'
        if string_to_find in attachment['raw']:
            tree = etree.fromstring(attachment['raw'])
            reason_node = tree.findtext('.//{*}Response/{*}Status/{*}StatusReason')
            if "Electronic ID:" in reason_node:
                original_document_id = reason_node[reason_node.find("Electronic ID:") + 15:reason_node.find("Electronic ID:") + 22]
                return (original_document_id, reason_node)
            return 'not_found'
        return False

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
            'hrextac': "urn:hzn.hr:schema:xsd:HRExtensionAggregateComponents-1",
        })
        return nsmap

    def _export_invoice_constraints_new(self, invoice, vals):
        constraints = super()._export_invoice_constraints_new(invoice, vals)
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
        tax_subtotals = document_node['cac:TaxTotal'][0]['cac:TaxSubtotal']
        hr_tax_subtotals = []
        cash_basis_line = False
        for i in range(len(tax_subtotals)):
            # Removing the HR-specific node from the normal subtotal where we calculate it
            hr_tax_name = tax_subtotals[i]['cac:TaxCategory'][0].pop('cbc:Name')
            cash_basis_flag = tax_subtotals[i]['cac:TaxCategory'][0].pop('hrextac:HRObracunPDVPoNaplati')  # Ensure pop() always runs
            cash_basis_line = cash_basis_line or cash_basis_flag
            new_item = {
                'cbc:TaxableAmount': tax_subtotals[i]['cbc:TaxableAmount'],
                'cbc:TaxAmount': tax_subtotals[i]['cbc:TaxAmount'],
                'hrextac:HRTaxCategory': {
                    'cbc:ID': tax_subtotals[i]['cac:TaxCategory'][0]['cbc:ID'],
                    'cbc:Name': hr_tax_name,
                    'cbc:Percent': tax_subtotals[i]['cac:TaxCategory'][0]['cbc:Percent'],
                    'cbc:TaxExemptionReasonCode': tax_subtotals[i]['cac:TaxCategory'][0]['cbc:TaxExemptionReasonCode'],
                    'cbc:TaxExemptionReason': tax_subtotals[i]['cac:TaxCategory'][0]['cbc:TaxExemptionReason'],
                    'hrextac:HRTaxScheme': tax_subtotals[i]['cac:TaxCategory'][0]['cac:TaxScheme'] if hr_tax_name['_text'] != "HR:POVNAK" else {'_text': "OTH"},
                }
            }
            hr_tax_subtotals.append(new_item)
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
                            'hrextac:HRTaxTotal': {
                                'cbc:TaxAmount': document_node['cac:TaxTotal'][0]['cbc:TaxAmount'],
                                'hrextac:HRTaxSubtotal': hr_tax_subtotals,
                            },
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
        line = vals['base_line']['record']
        # HR-BR-25: Each item MUST have an item classification identifier from the Classification of Products
        # by Activities scheme: KPD (CPA) - listID "CG", except in the case of advance payment invoices.
        line_node['cac:Item'].update({
            'cac:CommodityClassification': {
                'cbc:ItemClassificationCode': {
                    'listID': 'CG',
                    '_text': line.l10n_hr_kpd_category_id.name
                }
            }
        })

    def _get_party_node(self, vals):
        party_node = super()._get_party_node(vals)
        commercial_partner = vals['partner'].commercial_partner_id
        if commercial_partner.l10n_hr_personal_oib:
            if commercial_partner.l10n_hr_business_unit_code:
                party_node['cac:PartyIdentification']['cbc:ID'].update({
                    '_text': '9934:' + commercial_partner.l10n_hr_personal_oib + '::HR99:' + commercial_partner.l10n_hr_business_unit_code
                })
            else:
                party_node['cac:PartyIdentification']['cbc:ID'].update({
                    '_text': '9934:' + commercial_partner.l10n_hr_personal_oib
                })
        elif commercial_partner.company_registry:
            party_node['cac:PartyIdentification']['cbc:ID'].update({
                '_text': '0088:' + commercial_partner.company_registry
            })
        return party_node

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        super()._add_invoice_accounting_supplier_party_nodes(document_node, vals)
        invoice = vals['invoice']
        # HR-BR-37: Invoice must contain HR-BT-4: Operator code in accordance with the Fiscalization Act.
        # HR-BR-9: Invoice must contain HR-BT-5: Operator OIB in accordance with the Fiscalization Act.
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

    def _get_tax_category_code(self, customer, supplier, tax):
        # HR-BR-11: Each document-level expense (BG-21) that is not subject to VAT or is exempt from VAT must have
        # a document-level expense VAT category code (HR-BT-6) from table HR-TB-2 HR VAT category codes
        #   Instead of determining what the elements should be from the invoice details, here we directly use
        #   the data of the VAT expence category defined on the tax by the user
        hr_category = tax.l10n_hr_tax_category_id if tax else None
        if hr_category and tax.amount == 0:
            return hr_category.code_untdid
        else:
            return super()._get_tax_category_code(customer, supplier, tax)

    def _get_tax_exemption_reason(self, customer, supplier, tax):
        # HR-BR-11: Each document-level expense (BG-21) that is not subject to VAT or is exempt from VAT must have
        # a document-level expense VAT category code (HR-BT-6) from table HR-TB-2 HR VAT category codes
        res = super()._get_tax_exemption_reason(customer, supplier, tax)
        hr_category = tax.l10n_hr_tax_category_id if tax else None
        if hr_category:
            res.update({
                'name': hr_category.name,
            })
            if tax.amount == 0:
                tax_extension = 'ubl_cii_tax_exemption_reason_code' in tax._fields and tax.ubl_cii_tax_exemption_reason_code
                # If account_edi_ubl_cii_tax_extension is installed and a value is specified, use that data, if not, override with HR data
                if not tax_extension:
                    res.update({'tax_exemption_reason': hr_category.description})
        return res

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        # Override to include fields that are needed for HR
        customer = vals['customer']
        supplier = vals['supplier']
        if tax_data and (
            tax_data['tax'].amount_type != 'percent'
            or self._ubl_is_recycling_contribution_tax(tax_data)
        ):
            return
        elif tax_data:
            tax = tax_data['tax']
            return {
                'tax_category_code': self._get_tax_category_code(customer.commercial_partner_id, supplier, tax),
                **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, tax),
                'percent': tax.amount,
                'scheme_id': 'VAT',
                'is_withholding': tax.amount < 0.0,
                'currency': currency,
                'tax_exigibility': tax.tax_exigibility,
                'invoice_legal_notes': tax.invoice_legal_notes,
            }
        else:
            return {
                'tax_category_code': self._get_tax_category_code(customer.commercial_partner_id, supplier, self.env['account.tax']),
                **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, self.env['account.tax']),
                'percent': 0.0,
                'scheme_id': 'VAT',
                'is_withholding': False,
                'currency': currency,
                'tax_exigibility': False,
                'invoice_legal_notes': False,
            }

    def _ubl_get_tax_category_node(self, vals, tax_category):
        # Override the node 'cac:TaxCategory' in 'cac:SubTotal' to include fields that are needed for HR
        return {
            'cbc:ID': {'_text': tax_category['tax_category_code']},
            'cbc:Name': {'_text': tax_category.get('name')},
            'cbc:Percent': {'_text': tax_category['percent']},
            'cbc:TaxExemptionReasonCode': {'_text': tax_category.get('tax_exemption_reason_code')},
            'cbc:TaxExemptionReason': {'_text': tax_category.get('tax_exemption_reason')},
            'cac:TaxScheme': {
                'cbc:ID': {'_text': tax_category['scheme_id']},
            },
            'hrextac:HRObracunPDVPoNaplati': {'_text': html2plaintext(tax_category['invoice_legal_notes'] or "Obračun po naplaćenoj naknadi")} if tax_category['tax_exigibility'] == 'on_payment' else None
        }

    def _ubl_get_line_item_node_classified_tax_category_node(self, vals, tax_category):
        # Override the node 'cac:ClassifiedTaxCategory' in 'cac:Item' to include fields that are needed for HR
        return {
            'cbc:ID': {'_text': tax_category['tax_category_code']},
            'cbc:Name': {'_text': tax_category.get('name')},
            'cbc:Percent': {'_text': tax_category['percent']},
            'cbc:TaxExemptionReasonCode': {'_text': tax_category.get('tax_exemption_reason_code')},
            'cbc:TaxExemptionReason': {'_text': tax_category.get('tax_exemption_reason')},
            'cac:TaxScheme': {
                'cbc:ID': {'_text': tax_category['scheme_id']},
            }
        }

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        super()._add_document_line_tax_category_nodes(line_node, vals)
        for item in line_node['cac:Item']['cac:ClassifiedTaxCategory']:
            item.pop('hrextac:HRObracunPDVPoNaplati')

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

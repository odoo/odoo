from odoo import _, fields, models


class AccountEdiXmlUBLHR(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'
    _name = 'account.edi.xml.ubl_hr'
    _description = 'CIUS HR'

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_hr.xml"

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        if vals['document_type'] in ['invoice', 'credit_note']:
            # HR-BT-1: Copy indicator - is the invoice the original or already sent
            #   This doesn't appear to be currently supported in Odoo, and is set to 'false' in TR localization using a similar format
            vals['vals'].update({'copy_indicator': 'false'})
            # HR-BT-2: The invoice must have an invoice issuance time.
            #   (in addition to BT-2: Date of issue)
            vals['vals'].update({
                'issue_date': fields.Datetime.to_string(invoice.invoice_date).split()[0],
                'issue_time': fields.Datetime.to_string(invoice.invoice_date).split()[1],
            })
            # HR-BT-4: In the case of a positive amount due for payment (BT-115), the payment due date (BT-9) must be specified.
            if invoice.amount_residual > 0 and not vals['vals']['due_date']:
                if invoice.invoice_date_due:
                    vals['vals'].update({'due_date': invoice.invoice_date_due})
            # HR-BR-34: The process label MUST be specified. Values P1-P12 or P99:Customer ID from Table 4 Business Process Types are used.
            if invoice.l10n_hr_process_type == 'P99':
                vals['vals'].update({'profile_id': f"P99:{invoice.commercial_partner_id.name}"})
            else:
                vals['vals'].update({'profile_id': invoice.l10n_hr_process_type})
            # HR-BR-5: The specification identifier must have the value
            # 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0'
            vals['vals'].update({'customization_id': 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0'})
            # HR-BR-6: Each previous invoice reference (BG-3) must have the date of issue of the previous invoice (BT-26).
            # HR-BT-3: Note on previous invoice
            if invoice.reversed_entry_id:
                vals['vals']['billing_reference_vals'].update({'issue_date': invoice.reversed_entry_id.invoice_date})
            # HR-BR-37: Invoice must contain HR-BT-4: Operator code in accordance with the Fiscalization Act.
            # HR-BR-9: Invoice must contain HR-BT-5: Operator OIB in accordance with the Fiscalization Act.
            vals['vals']['accounting_supplier_party_vals'].update({
                'operator_oib': invoice.l10n_hr_operator_oib,
                'operator_name': invoice.l10n_hr_operator_name,
            })
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals=vals)
        if vals['document_type'] in ['invoice', 'credit_note']:
            if any(any(c.isspace() for c in v['payee_financial_account_vals']['id']) for v in vals['vals']['payment_means_vals_list']):
                constraints.update({'ubl_hr_br_1': _("HR-BR-1: The account number must not contain whitespace characters.")})
            if invoice.amount_residual > 0 and not vals['vals']['due_date']:
                if not invoice.invoice_date_due:
                    constraints.update({'ubl_hr_br_4': _("HR-BT-4: In the case of a positive amount due for payment (BT-115), the payment due date (BT-9) must be specified.")})
            constraints.update({
                'ubl_hr_bt_7_seller_email_required': self._check_required_fields(vals['vals']['accounting_supplier_party_vals']['party_vals']['contact_vals'], 'electronic_mail'),
                'ubl_hr_bt_10_buyer_email_required': self._check_required_fields(vals['vals']['accounting_customer_party_vals']['party_vals']['contact_vals'], 'electronic_mail'),
                'ubl_hr_br_buyer_vat_required': self._check_required_fields(vals['vals']['accounting_customer_party_vals']['party_vals']['party_tax_scheme_vals'][0], 'company_id'),
            })
        return constraints

    def _get_tax_unece_codes(self, customer, supplier, tax):
        # Overrides _get_tax_unece_codes() for Croatia
        # HR-BR-11: Each document-level expense (BG-21) that is not subject to VAT or is exempt from VAT must have
        # a document-level expense VAT category code (HR-BT-6) from table HR-TB-2 HR VAT category codes
        #   Instead of determining what the elements should be from the invoice details, here we directly use
        #   the data of the VAT expence category defined on the tax by the user
        hr_category = tax.l10n_hr_vat_expence_category_id
        if hr_category:
            return {
                'tax_category_code': hr_category.code_untdid,
                'tax_exemption_reason_code': hr_category.name,
                'tax_exemption_reason': hr_category.description,
            }
        else:
            return {}

    # -------------------------------------------------------------------------
    # EXPORT: New (dict_to_xml) helpers
    # -------------------------------------------------------------------------

    def _export_invoice(self, invoice, convert_fixed_taxes=True):
        # Override that enables refractored XML generation for HR invoices
        # Only backend switching at the moment
        if self._name == 'account.edi.xml.ubl_hr':
            return self._export_invoice_new(invoice)
        return super()._export_invoice(invoice, convert_fixed_taxes=convert_fixed_taxes)

    def _get_invoice_node(self, vals):
        document_node = super()._get_invoice_node(vals)
        invoice = vals['invoice']
        # HR-BT-1: Copy indicator - is the invoice the original or already sent
        #   This doesn't appear to be currently supported in Odoo, and is set to 'false' in TR localization using a similar format
        document_node.update({
            'cbc:CopyIndicator': {
                '_text': 'false'
            }
        })
        # HR-BT-2: The invoice must have an invoice issuance time.
        #   (in addition to BT-2: Date of issue)
        document_node.update({
            'cbc:IssueDate': {
                '_text': fields.Datetime.to_string(invoice.invoice_date).split()[0]
            },
            'cbc:IssueTime': {
                '_text': fields.Datetime.to_string(invoice.invoice_date).split()[1]
            }
        })
        # HR-BT-4: In the case of a positive amount due for payment (BT-115), the payment due date (BT-9) must be specified.
        if invoice.amount_residual > 0 and not document_node['cbc:DueDate'] and vals['document_type'] == 'invoice':
            if invoice.invoice_date_due:
                document_node.update({
                    'cbc:DueDate': {
                        '_text': invoice.invoice_date_due
                    }
                })
        # HR-BR-34: The process label MUST be specified. Values P1-P12 or P99:Customer ID from Table 4 Business Process Types are used.
        document_node.update({
            'cbc:ProfileID': {
                '_text': f"P99:{invoice.commercial_partner_id.name}" if invoice.l10n_hr_process_type == 'P99' else invoice.l10n_hr_process_type
            }
        })
        # HR-BR-5: The specification identifier must have the value
        # 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0'
        document_node.update({
            'cbc:CustomizationID': {
                '_text': 'urn:cen.eu:en16931:2017#compliant#urn:mfin.gov.hr:cius-2025:1.0#conformant#urn:mfin.gov.hr:ext-2025:1.0'
            }
        })
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
        # HR-BR-6: Each previous invoice reference (BG-3) must have the date of issue of the previous invoice (BT-26).
        # HR-BT-3: Note on previous invoice
        if invoice.reversed_entry_id:
            document_node['cac:BillingReference'].update({
                'cbc:IssueDate': {
                    '_text': invoice.reversed_entry_id.invoice_date
                    }
                })
        return document_node

    def _get_tax_category_code(self, customer, supplier, tax):
        # HR-BR-11: Each document-level expense (BG-21) that is not subject to VAT or is exempt from VAT must have
        # a document-level expense VAT category code (HR-BT-6) from table HR-TB-2 HR VAT category codes
        #   Instead of determining what the elements should be from the invoice details, here we directly use
        #   the data of the VAT expence category defined on the tax by the user
        hr_category = tax.l10n_hr_vat_expence_category_id if tax else None
        if hr_category:
            return hr_category.code_untdid
        else:
            return super()._get_tax_category_code(customer, supplier, tax)

    def _get_tax_exemption_reason(self, customer, supplier, tax):
        # HR-BR-11: Each document-level expense (BG-21) that is not subject to VAT or is exempt from VAT must have
        # a document-level expense VAT category code (HR-BT-6) from table HR-TB-2 HR VAT category codes
        hr_category = tax.l10n_hr_vat_expence_category_id if tax else None
        if hr_category:
            return {
                'tax_exemption_reason': hr_category.description,
                'tax_exemption_reason_code': hr_category.name,
            }
        else:
            return super()._get_tax_exemption_reason(customer, supplier, tax)

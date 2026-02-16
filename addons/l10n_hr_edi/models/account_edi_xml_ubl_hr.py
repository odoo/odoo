# UBL structure for CIUS HR
# Old vals dict structure for 17.0

from odoo import _, fields, models
from lxml import etree


class AccountEdiXmlUBLHR(models.AbstractModel):
    _inherit = 'account.edi.xml.ubl_bis3'
    _name = 'account.edi.xml.ubl_hr'
    _description = "CIUS HR"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_hr.xml"

    def _export_invoice_vals(self, invoice):
        vals = super()._export_invoice_vals(invoice)
        vals['main_template'] = {
            'account_edi_ubl_cii.ubl_20_Invoice': 'l10n_hr_edi.ubl_hr_Invoice',
            'account_edi_ubl_cii.ubl_20_CreditNote': 'l10n_hr_edi.ubl_hr_CreditNote',
            'account_edi_ubl_cii.ubl_20_DebitNote': 'l10n_hr_edi.ubl_hr_DebitNote'
        }.get(vals['main_template'], vals['main_template'])
        vals.update({
            'HrExtensionType_template': 'l10n_hr_edi.ubl_hr_HrExtensionType',
            'HrTaxCategoryType_template': 'l10n_hr_edi.ubl_hr_HrTaxCategoryType',
            'TaxCategoryType_template': 'l10n_hr_edi.ubl_hr_TaxCategoryType',
        })
        if vals['document_type'] in ['invoice', 'credit_note']:
            # For Croatia, ID should be the Croatian-format fiscalization number
            vals['vals'].update({'id': invoice.l10n_hr_fiscalization_number})
            # HR-BT-1: Copy indicator - is the invoice the original or already sent
            #   This doesn't appear to be currently supported in Odoo, and is set to 'false' in TR localization using a similar format
            vals['vals'].update({'copy_indicator': 'false'})
            # HR-BT-2: The invoice must have an invoice issuance time.
            #   (in addition to BT-2: Date of issue)
            vals['vals'].update({
                'issue_date': fields.Datetime.to_string(invoice.l10n_hr_invoice_sending_time).split()[0],
                'issue_time': fields.Datetime.to_string(invoice.l10n_hr_invoice_sending_time).split()[1],
            })
            # HR-BT-4: In the case of a positive amount due for payment (BT-115), the payment due date (BT-9) must be specified.
            if invoice.amount_residual > 0 and not vals['vals']['due_date']:
                if invoice.invoice_date_due:
                    vals['vals'].update({'due_date': invoice.invoice_date_due})
            # HR-BR-34: The process label MUST be specified. Values P1-P12 or P99:Customer ID from Table 4 Business Process Types are used.
            vals['vals'].update({'profile_id': f"P99:{invoice.l10n_hr_customer_defined_process_name}" if invoice.l10n_hr_process_type == 'P99' else invoice.l10n_hr_process_type})
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
            # Document Type Codes and Process Type Logic
            if invoice.l10n_hr_process_type in ('P4', 'P6'):
                vals['vals']['document_type_code'] = '386'
            elif invoice.l10n_hr_process_type == 'P9':
                vals['vals']['document_type_code'] = '381'
            cash_basis_flag = any(any(tax.tax_exigibility == 'on_payment' for tax in line.tax_ids) for line in invoice.line_ids)
            self._export_hrextac_vals(vals['vals'], cash_basis_flag)
            for total in vals['vals'].get('tax_total_vals', []):
                for subtotal in total.get('tax_subtotal_vals', []):
                    if subtotal['tax_category_vals'].get('name'):
                        subtotal['tax_category_vals'].pop('name')
        return vals

    def _export_invoice_constraints(self, invoice, vals):
        constraints = super()._export_invoice_constraints(invoice, vals=vals)
        if vals['document_type'] in ['invoice', 'credit_note']:
            if invoice.partner_bank_id:
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

    def _get_tax_unece_codes(self, invoice, tax):
        # Overrides _get_tax_unece_codes() for Croatia
        # HR-BR-11: Each document-level expense (BG-21) that is not subject to VAT or is exempt from VAT must have
        # a document-level expense VAT category code (HR-BT-6) from table HR-TB-2 HR VAT category codes
        #   Instead of determining what the elements should be from the invoice details, here we directly use
        #   the data of the VAT expence category defined on the tax by the user
        res = super()._get_tax_unece_codes(invoice, tax)
        hr_category = tax.l10n_hr_tax_category_id
        tax_extension = 'ubl_cii_tax_exemption_reason_code' in tax._fields and tax.ubl_cii_tax_exemption_reason_code
        if hr_category:
            res.update({
                'hr_tax_name': hr_category.name,
                'hr_tax_category_code': hr_category.code_untdid,
                'hr_tax_exemption_reason': hr_category.description,
            })
            if not tax_extension and tax.amount == 0:
                res.update({
                    'tax_category_code': hr_category.code_untdid,
                    'tax_exemption_reason': hr_category.description,
                })
        return res

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        # Overrides BIS 3 version
        product = line.product_id
        taxes = line.tax_ids.flatten_taxes_hierarchy().filtered(lambda t: t.amount_type != 'fixed')
        tax_category_vals_list = self._get_tax_category_list(line.move_id, taxes)
        description = line.name and line.name.replace('\n', ', ')
        return {
            'description': description,
            'name': product.name or description,
            'sellers_item_identification_vals': {'id': product.code},
            'classified_tax_category_vals': tax_category_vals_list,
            'standard_item_identification_vals': {
                'id': product.barcode,
                'id_attrs': {'schemeID': '0160'},  # GTIN
            } if product.barcode else {},
            'commodity_classification_vals': [{
                'item_classification_attrs': {'listID': 'CG'},
                'item_classification_code': line.l10n_hr_kpd_category_id.name,
            }]
        }

    def _get_partner_party_identification_vals_list(self, partner):
        vals = super()._get_partner_party_identification_vals_list(partner)
        if partner.l10n_hr_personal_oib:
            if partner.l10n_hr_business_unit_code:
                party_ident = '9934:' + partner.l10n_hr_personal_oib + '::HR99:' + partner.l10n_hr_business_unit_code
            else:
                party_ident = '9934:' + partner.l10n_hr_personal_oib
        elif partner.company_registry:
            party_ident = '0088:' + partner.company_registry
        else:
            party_ident = False
        if party_ident:
            vals.append({
                    'id': party_ident,
                })
        return vals

    def _get_tax_category_list(self, invoice, taxes):
        # OVERRIDES Bis3
        res = []
        for tax in taxes:
            tax_unece_codes = self._get_tax_unece_codes(invoice, tax)
            res.append({
                'id': tax_unece_codes.get('tax_category_code'),
                'percent': tax.amount if tax.amount_type == 'percent' else False,
                'name': tax.l10n_hr_tax_category_id.name if tax.l10n_hr_tax_category_id else tax_unece_codes.get('tax_exemption_reason'),
                'tax_scheme_vals': {'id': 'VAT'},
                **tax_unece_codes,
            })
        return res

    def _export_hrextac_vals(self, vals, cash_basis_flag):
        hrextac_vals = vals.get('tax_total_vals', []).copy()
        for item in hrextac_vals:
            item.update({
                'hr_cash_basis_flag': "Obračun po naplaćenoj naknadi" if cash_basis_flag else False,
                'hr_tax_exclusive_amount': vals.get('monetary_total_vals', {}).get('tax_exclusive_amount'),
                'hr_out_of_scope_amount': 0.0,  # Currently unsupported
            })
        vals.update({
            'hrextac_vals': hrextac_vals
        })

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_fill_invoice_form(self, invoice, tree, qty_factor):
        logs = super()._import_fill_invoice_form(invoice=invoice, tree=tree, qty_factor=qty_factor)
        profile_id_node = tree.find('./{*}ProfileID')
        if profile_id_node is not None:
            invoice.l10n_hr_process_type = profile_id_node.text[:3] if profile_id_node.text[:3] == 'P99' else profile_id_node.text
            invoice.l10n_hr_customer_defined_process_name = profile_id_node.text[4:] if profile_id_node.text[:3] == 'P99' else False
        fiscalization_number_node = tree.find('./{*}ID')
        if fiscalization_number_node is not None:
            invoice.l10n_hr_edi_addendum_id.write({'fiscalization_number': fiscalization_number_node.text})
        return logs

    def _import_fill_invoice_line_values(self, tree, xpath_dict, invoice_line, qty_factor):
        line_vals = super()._import_fill_invoice_line_values(tree=tree, xpath_dict=xpath_dict, invoice_line=invoice_line, qty_factor=qty_factor)
        kpd_category_node = tree.find('./{*}Item/{*}CommodityClassification/{*}ItemClassificationCode')
        if kpd_category_node is not None:
            line_kpd_category = self.env['l10n_hr.kpd.category'].search([('name', '=', kpd_category_node.text)], limit=1)
            if line_kpd_category:
                line_vals.update({
                    'l10n_hr_kpd_category_id': line_kpd_category.id,
                })
        return line_vals

    def _import_fill_invoice_line_taxes(self, tax_nodes, invoice_line, inv_line_vals, logs):
        logs = super()._import_fill_invoice_line_taxes(tax_nodes=tax_nodes, invoice_line=invoice_line, inv_line_vals=inv_line_vals, logs=logs)
        invoice_line.l10n_hr_kpd_category_id = inv_line_vals.get('l10n_hr_kpd_category_id')
        return logs

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

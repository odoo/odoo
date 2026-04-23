import uuid
from collections import defaultdict

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _l10n_sa_is_phase_2_applicable(self, check_document=True):
        return self._l10n_sa_is_phase_1_applicable() and self.is_sale_document() and self.state == 'posted' and \
               self.journal_id._l10n_sa_ready_to_submit_einvoices() and (self.l10n_sa_edi_document_id or not check_document)

    @api.ondelete(at_uninstall=False)
    def _prevent_zatca_rejected_invoice_deletion(self):
        # Prevent deletion of ZATCA-rejected invoices in production mode
        descr = 'Rejected ZATCA Document not to be deleted - ثيقة ZATCA المرفوضة لا يجوز حذفها'
        for move in self:
            if move.country_code == "SA" and \
               move.company_id.l10n_sa_edi_is_production and \
               move.attachment_ids.filtered(lambda a: a.description == descr and a.res_model == 'account.move'):
                raise UserError(_("The Invoice(s) are linked to a validated EDI document and cannot be modified according to ZATCA rules"))

    def _l10n_sa_get_alerts(self):
        res = {}
        invalid_moves_dict = defaultdict(lambda: self.env['account.move'])
        invalid_moves_msg_dict = {
            'l10n_sa_edi_invalid_partner': self.env._("Invoice cannot be posted as the Supplier and Buyer are the same."),
            'l10n_sa_edi_no_tax_lines': self.env._("Invoice lines need at least one tax. Please input it and try again."),
            'l10n_sa_edi_invalid_date_moves': self.env._("Please set the Invoice Date to be either less than or equal to today as per the Asia/Riyadh time zone, since ZATCA does not allow future-dated invoicing."),
            'l10n_sa_edi_empty_reason_moves': self.env._("Please make sure the 'ZATCA Reason' for the issuance of the Credit/Debit Note is specified."),
            'l10n_sa_edi_invalid_ref_moves': self.env._("Please make sure the 'Customer Reference' contains the sequential number of the original invoice(s) that the Credit/Debit Note is related to."),
        }
        invalid_scheme_partners = self.env['res.partner']
        empty_vat_partners = self.env['res.partner']

        edi_moves = self.filtered(lambda move: move._l10n_sa_is_phase_2_applicable())
        for move in edi_moves:
            if move.commercial_partner_id == move.company_id.partner_id.commercial_partner_id:
                invalid_moves_dict['l10n_sa_edi_invalid_partner'] += move

            if invalid_lines := move.invoice_line_ids.filtered(lambda line: line.display_type == 'product' and line._check_edi_line_tax_required() and not line.tax_ids):
                invalid_moves_dict['l10n_sa_edi_no_tax_lines'] |= invalid_lines.move_id

            if move.invoice_date > fields.Date.context_today(self.with_context(tz='Asia/Riyadh')):
                invalid_moves_dict['l10n_sa_edi_invalid_date_moves'] += move

            if move.l10n_sa_show_reason and not move.l10n_sa_reason:
                invalid_moves_dict['l10n_sa_edi_empty_reason_moves'] += move

            if move.l10n_sa_show_reason and not move._l10n_sa_check_billing_reference():
                invalid_moves_dict['l10n_sa_edi_invalid_ref_moves'] += move

            if (
                any(
                    tax.l10n_sa_exemption_reason_code in ('VATEX-SA-HEA', 'VATEX-SA-EDU')
                    for tax in move.invoice_line_ids.filtered(
                        lambda line: line.display_type == 'product',
                    ).tax_ids
                )
                and (
                    move.commercial_partner_id.l10n_sa_edi_additional_identification_scheme != 'NAT'
                    or not move.commercial_partner_id.l10n_sa_edi_additional_identification_number
                )
            ):
                invalid_scheme_partners |= move.commercial_partner_id

            if move.commercial_partner_id.l10n_sa_edi_additional_identification_scheme == 'TIN' and not move.commercial_partner_id.vat:
                empty_vat_partners |= move.commercial_partner_id

        for error_key, error_moves in invalid_moves_dict.items():
            res[error_key] = {
                'message': invalid_moves_msg_dict[error_key],
                'level': 'danger',
                'action_text': self.env._("View Invoices"),
                'action': error_moves._get_records_action(),
            }

        if invalid_journals := edi_moves.journal_id.filtered(lambda journal: not journal._l10n_sa_ready_to_submit_einvoices()):
            res['l10n_sa_edi_journals_not_onboarded'] = {
                'message': self.env._("The Journals are not onboarded yet. Please onboard them and try again."),
                'level': 'danger',
                'action_text': self.env._("View Journals"),
                'action': invalid_journals._get_records_action(),
            }

        if invalid_companies := edi_moves.company_id.filtered(lambda company: not company._l10n_sa_check_organization_unit()):
            res['l10n_sa_edi_company_vat_invalid'] = {
                'message': self.env._("The company VAT identification must contain 15 digits, with the first and last digits being '3' as per the BR-KSA-39 and BR-KSA-40 of ZATCA KSA business rule."),
                'level': 'danger',
                'action_text': self.env._("View Companies"),
                'action': invalid_companies._get_records_action(),
            }

        if invalid_companies := edi_moves.journal_id.company_id.sudo().filtered(lambda company: not company.l10n_sa_private_key_id):
            res['l10n_sa_edi_company_key_invalid'] = {
                'message': self.env._("No Private Key was generated for these companies. A Private Key is mandatory in order to generate Certificate Signing Requests (CSR)."),
                'level': 'danger',
                'action_text': self.env._("View Companies"),
                'action': invalid_companies._get_records_action(),
            }

        if invalid_scheme_partners:
            res['l10n_sa_edi_invalid_scheme_customers'] = {
                'message': self.env._("""
                    Please set the Identification Scheme as National ID and Identification Number as the respective
                    number on the Customer, as the Tax Exemption Reason is set either as VATEX-SA-HEA or VATEX-SA-EDU
                """),
                'level': 'danger',
                'action_text': self.env._("View Partners"),
                'action': invalid_scheme_partners._get_records_action(),
            }

        if empty_vat_partners:
            res['l10n_sa_edi_empty_vat_customers'] = {
                'message': self.env._("Please set the VAT Number as the Identification Scheme is Tax Identification Number"),
                'level': 'danger',
                'action_text': self.env._("View Partners"),
                'action': empty_vat_partners._get_records_action(),
            }

        return res

    def _l10n_sa_handle_alerts(self):
        return self.action_send_and_print()

    def _l10n_sa_check_billing_reference(self):
        """
        Make sure credit/debit notes have a either a reveresed move or debited move or a customer reference
        """
        self.ensure_one()
        return self.debit_origin_id or self.reversed_entry_id or self.ref

    @api.depends('state')
    def _compute_show_reset_to_draft_button(self):
        """
        Override to hide the Reset to Draft button for ZATCA Invoices that have been successfully submitted
        in Production mode.
        """
        super()._compute_show_reset_to_draft_button()
        for move in self:
            # The "Reset to Draft" button should be hidden in the following cases:
            # - Invoice has been successfully submitted in Production mode.
            # - The invoice submission encountered a timed out, regardless of the API mode.
            if move.l10n_sa_chain_index and (move.company_id.l10n_sa_edi_is_production or not move.l10n_sa_edi_document_id._l10n_sa_is_in_chain()):
                move.show_reset_to_draft_button = False

    def _post(self, soft=True):
        res = super()._post(soft)
        for record in self.filtered(lambda rec: rec._l10n_sa_is_phase_2_applicable(check_document=False)):
            record._l10n_sa_edi_create_document()
        return res

    def button_draft(self):
        # OVERRIDE
        if any(move.country_code == "SA" and move.l10n_sa_chain_index and move.company_id.l10n_sa_edi_is_production for move in self):
            raise UserError(self.env._("The Invoice(s) are linked to a validated EDI document and cannot be modified according to ZATCA rules"))

        res = super().button_draft()
        self.filtered(lambda move: move.country_code == "SA").l10n_sa_edi_document_id.write({
            'state': 'to_send',
            'l10n_sa_chain_index': False,
        })

        return res

    def _l10n_sa_generate_unsigned_data(self):
        """
        Generate UUID and digital signature to be used during both Signing and QR code generation.
        It is necessary to save the signature as it changes everytime it is generated and both the signing and the
        QR code expect to have the same, identical signature.
        """
        self.ensure_one()
        # Build the dict of values to be used for generating the Invoice XML content
        # Set Invoice field values required for generating the XML content, hash and signature
        self.l10n_sa_uuid = uuid.uuid4()
        # We generate the XML content
        xml_content = self._l10n_sa_generate_zatca_template()
        if isinstance(xml_content, dict):
            raise ValidationError(xml_content.get('error'))
        # Once the required values are generated, we hash the invoice, then use it to generate a Signature
        invoice_hash_hex = self.env['account.edi.xml.ubl_21.zatca']._l10n_sa_generate_invoice_xml_hash(xml_content).decode()
        self.l10n_sa_invoice_signature = self.env['l10n_sa_edi.document']._l10n_sa_get_digital_signature(self.journal_id.company_id,
                                                                                   invoice_hash_hex).decode()
        return xml_content

    def _is_l10n_sa_eligibile_invoice(self):
        self.ensure_one()
        return self.is_invoice() and self.l10n_sa_confirmation_datetime and self.country_code == 'SA'

    def _l10n_sa_is_legal(self):
        # Extends l10n_sa
        # Accounts for both ZATCA phases
        # Phase 1: no documents
        # Phase 2: checks the state of documents
        self.ensure_one()
        result = super()._l10n_sa_is_legal()
        zatca_document = self.l10n_sa_edi_document_id
        return result or (self.company_id.country_id.code == 'SA' and zatca_document and self.l10n_sa_edi_state in {"accepted", "warning"})

    def _get_report_base_filename(self):
        """
        Generate the name of the invoice PDF file according to ZATCA business rules:
        Seller Vat Number (BT-31), Date (BT-2), Time (KSA-25), Invoice Number (BT-1)
        """
        if self._is_l10n_sa_eligibile_invoice():
            return self.with_context(l10n_sa_file_format=False).env['account.edi.xml.ubl_21.zatca']._export_invoice_filename(self)
        return super()._get_report_base_filename()

    def _get_invoice_report_filename(self, extension='pdf', report=None):
        if self._is_l10n_sa_eligibile_invoice():
            return self.with_context(l10n_sa_file_format=extension).env['account.edi.xml.ubl_21.zatca']._export_invoice_filename(self)
        return super()._get_invoice_report_filename(extension, report)

    def _prepare_tax_lines_for_taxes_computation(self, tax_amls, round_from_tax_lines):
        """
        If the final invoice has downpayment lines, we skip the tax correction, as we need to recalculate tax amounts
        without taking into account those lines
        """
        if self.country_code == 'SA' and not self._is_downpayment() and self.line_ids._get_downpayment_lines():
            return []
        return super()._prepare_tax_lines_for_taxes_computation(tax_amls, round_from_tax_lines)

    def _get_l10n_sa_totals(self):
        self.ensure_one()
        invoice_node = self.env['account.edi.xml.ubl_21.zatca']._get_invoice_node({'invoice': self})
        return {
            'total_amount': invoice_node['cac:LegalMonetaryTotal']['cbc:TaxInclusiveAmount']['_text'],
            'total_tax': invoice_node['cac:TaxTotal'][-1]['cbc:TaxAmount']['_text'],
        }

    def _get_l10n_sa_journal(self):
        self.ensure_one()
        return self.journal_id

    def action_open_chain_head(self):
        """
        Action to show the chain head of the invoice
        """
        self.ensure_one()
        return self.l10n_sa_edi_document_id.l10n_sa_edi_chain_head_id._get_records_action(name=self.env._("Chain Head"))

    def _l10n_sa_generate_zatca_template(self):
        """Render the ZATCA UBL file"""
        self.ensure_one()
        xml_content, errors = self.env['account.edi.xml.ubl_21.zatca']._export_invoice(self)
        if errors:
            return {
                'error': self.env._("Could not generate Invoice UBL content: %s", ", \n".join(errors)),
                'blocking_level': 'error',
            }

        return self.env['l10n_sa_edi.document']._l10n_sa_postprocess_zatca_template(xml_content)


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    @api.depends('price_subtotal', 'price_total')
    def _compute_tax_amount(self):
        super()._compute_tax_amount()
        AccountTax = self.env['account.tax']
        for line in self:
            if (
                line.move_id.country_code == 'SA'
                and line.move_id.is_invoice(include_receipts=True)
                and line.display_type == 'product'
            ):
                base_line = line.move_id._prepare_product_base_line_for_taxes_computation(line)
                AccountTax._add_tax_details_in_base_line(base_line, line.company_id)
                AccountTax._round_base_lines_tax_details([base_line], line.company_id)
                line.l10n_gcc_invoice_tax_amount = sum(
                    tax_data['tax_amount_currency']
                    for tax_data in base_line['tax_details']['taxes_data']
                    if tax_data['tax'].amount > 0
                )

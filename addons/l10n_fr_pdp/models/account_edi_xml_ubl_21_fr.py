from odoo import _, api, models
from odoo.tools.misc import formatLang
from odoo.tools import html2plaintext

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

PDP_CUSTOMIZATION_ID = 'urn:cen.eu:en16931:2017#conformant#urn.cpro.gouv.fr:1p0:extended-ctc-fr'  # Not accepted by SuperPDP due to missing validator

CPRO_CUSTOMIZATION_ID = 'urn:cen.eu:en16931:2017#conformant#urn.cpro.gouv.fr:1p0:extended-ctc-fr'
CPRO_INVOICE_IDENTIFIER = f'busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##{CPRO_CUSTOMIZATION_ID}::2.1'

PAID_STATES = frozenset({'in_payment', 'paid'})


class AccountEdiXmlUbl21Fr(models.AbstractModel):
    _name = "account.edi.xml.ubl_21_fr"
    _inherit = "account.edi.ubl_cen_en16931"
    _description = "France UBL 2.1 E-Invoicing Format"

    @api.model
    def _pdp_can_invoice_b2g(self, customer):
        # We use fields added in this module for B2G
        return self.env['ir.module.module']._get('l10n_fr_facturx_chorus_pro').state == 'installed'

    @api.model
    def _pdp_is_b2g(self, customer):
        # We put the identifier for chorus pro invoices in `peppol_supported_documents`
        # to mark the partner as B2G / "behind Chorus Pro"
        return CPRO_INVOICE_IDENTIFIER in (customer.peppol_supported_documents or [])

    @api.model
    def _pdp_needs_b2g_fields(self, customer):
        return self._pdp_can_invoice_b2g(customer) and self._pdp_is_b2g(customer)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_21_fr.xml"

    def _export_document_node_constraints(self, vals):
        # EXTENDS account.edi.ubl_cen_en16931
        invoice = vals['invoice']
        constraints = super()._export_document_node_constraints(vals)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]
            commercial_partner = partner.commercial_partner_id
            if commercial_partner.peppol_eas != '0225' or not commercial_partner.peppol_endpoint:
                constraints[f"ubl_21_fr_{partner_type}_pdp_identifier_required"] = self.env._("The following partner's PDP identifier is missing: %s", commercial_partner.display_name)
            id_type, id_value = commercial_partner._l10n_fr_pdp_get_base_identifier()
            if not id_type or not id_value:
                constraints[f"ubl_21_fr_{partner_type}_identifier_required"] = self.env._("The following partner's SIREN or SIRET is missing: %s", commercial_partner.display_name)

        if self._is_document(vals, 'credit_note') and not (invoice.reversed_entry_id.name or invoice.reversed_entry_id.invoice_date):
            constraints[f"ubl_21_fr_{partner_type}_refund_invoice_reference"] = self.env._("You cannot create a Credit Note without an original invoice: %s", vals['invoice'].name)

        customer = vals['customer'].commercial_partner_id
        if self._pdp_is_b2g(customer) and not self._pdp_can_invoice_b2g(customer):
            cpro_module_name = self.env['ir.module.module'].sudo()._get('l10n_fr_facturx_chorus_pro').display_name
            constraints["ubl_21_fr_cpro_module_missing"] = self.env._("This partner is behind Chorus PRO. Please install the module '%s'", cpro_module_name)

        billing_context = vals['document_node']['cbc:ProfileID']['_text']

        # [BR-FR-CO-07]-BT-9 Due date, if present, must not be before BT-2
        # Issue date, unless it's a down payment or the billing context is
        # B2/S2/M2 (already paid).
        if (
            invoice.invoice_date_due
            and invoice.invoice_date_due < invoice.invoice_date
            and not invoice._is_downpayment()
            and billing_context not in ('B2', 'S2', 'M2')
        ):
            constraints['ubl_21_fr_due_date_before_issue_date'] = self.env._(
                "The due date (%(due_date)s) cannot be before the issue date (%(issue_date)s).",
                due_date=invoice.invoice_date_due, issue_date=invoice.invoice_date,
            )

        # [BR-FR-CO-09]-If the billing context (BT-23) is B2/S2/M2, the paid
        # amount (BT-113) must equal the total (BT-112), the payable amount
        # (BT-115) must be 0 and the due date (BT-9) must be set.
        if billing_context in ('B2', 'S2', 'M2'):
            paid_amount = invoice.amount_total - invoice.amount_residual
            if invoice.currency_id.compare_amounts(paid_amount, invoice.amount_total) != 0:
                constraints['ubl_21_fr_billing_context_paid_amount'] = self.env._(
                    "Billing context %(context)s requires the paid amount to equal the total amount.",
                    context=billing_context,
                )
            if invoice.currency_id.compare_amounts(invoice.amount_residual, 0) != 0:
                constraints['ubl_21_fr_billing_context_payable_amount'] = self.env._(
                    "Billing context %(context)s requires the payable amount to be 0.",
                    context=billing_context,
                )
            if not invoice.invoice_date_due:
                constraints['ubl_21_fr_billing_context_due_date_required'] = self.env._(
                    "Billing context %(context)s requires the due date to be set.",
                    context=billing_context,
                )

        return constraints

    def _ubl_add_document_currency_code_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_document_currency_code_node(vals)
        vals['document_node']['cbc:DocumentCurrencyCode']['_text'] = vals['currency'].name

    def _ubl_add_invoice_header_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_invoice_header_nodes(vals)
        customer = vals['customer'].commercial_partner_id
        b2g = self._pdp_needs_b2g_fields(customer)

        invoice = vals['invoice']
        document_node = vals['document_node']

        profile_id = self._l10n_fr_pdp_get_profile_id(vals)
        document_node.update({
            'cbc:CustomizationID': {'_text': CPRO_CUSTOMIZATION_ID if b2g else PDP_CUSTOMIZATION_ID},
            'cbc:ProfileID': {'_text': profile_id},
        })

        # Add the invoice narration, if any.
        if invoice.narration:
            document_node['cbc:Note'].append({'_text': html2plaintext(invoice.narration)})

        # [BR-FR-05] Add mandatory notes with defaults if not already present
        # Add default notes
        for code, default_content in self._get_default_notes(vals).items():
            document_node['cbc:Note'].append({
                '_text': f"#{code}#{default_content}",
            })

        # Règles de gestion G1.52
        if self._is_document(vals, 'credit_note'):
            document_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': invoice.reversed_entry_id.name},
                    'cbc:IssueDate': {'_text': invoice.reversed_entry_id.invoice_date},
                }
            }

        # [BR-FR-CO-09/BT-23] : Si le cadre de facturation (BT-23) est B2, S2 ou M2, alors la date d'échéance (BT-9) doit être renseignée et correspondre à la date de paiement.
        # For credit notes, this is handled in `_add_invoice_payment_means_nodes` instead, as `cac:PaymentMeans` is
        # not populated yet at this point.
        if profile_id in ('B2', 'S2', 'M2') and not self._is_document(vals, 'credit_note'):
            document_node['cbc:DueDate'] = {'_text': invoice._pdp_get_payment_date() or invoice.invoice_date}

        # Profile ID X4 - Final invoice with downpayments
        if profile_id in ('B4', 'S4', 'M4'):
            downpayment_moves = invoice.invoice_line_ids._get_downpayment_lines().move_id.filtered(lambda m: m != invoice)
            document_node['cac:BillingReference'] = []
            for downpayment_move in downpayment_moves:
                document_node['cac:BillingReference'].append({
                    'cac:InvoiceDocumentReference': {
                        'cbc:ID': {'_text': downpayment_move.name},
                        'cbc:IssueDate': {'_text': downpayment_move.invoice_date},
                        'cbc:DocumentTypeCode': {'_text': 386 if downpayment_move.move_type == 'out_invoice' else 503},  # downpayment invoice or downpayment credit note
                    },
                })

        # B2G
        if not b2g:
            return

        if invoice.buyer_reference:
            document_node['cbc:BuyerReference'] = {'_text': invoice.buyer_reference}

        if invoice.purchase_order_reference:
            document_node['cac:OrderReference'] = {
                'cbc:ID': {'_text': invoice.purchase_order_reference}
            }

    def _ubl_add_payment_means_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_payment_means_nodes(vals)

        if not self._is_document(vals, 'credit_note'):
            return

        profile_id = self._l10n_fr_pdp_get_profile_id(vals)
        # [BR-FR-CO-09/BT-23] : Si le cadre de facturation (BT-23) est B2, S2 ou M2, alors la date d'échéance (BT-9) doit être renseignée et correspondre à la date de paiement.
        if profile_id in ('B2', 'S2', 'M2'):
            invoice = vals['invoice']
            payment_due_date = invoice._pdp_get_payment_date() or invoice.invoice_date
            for node in vals['document_node']['cac:PaymentMeans']:
                node['cbc:PaymentDueDate'] = {'_text': payment_due_date}

    def _ubl_add_invoice_type_code_node(self, vals):
        # Override account_edi_ubl: [BR-FR-04] Downpayment code for invoice is 386
        invoice = vals['invoice']
        vals['document_node']['cbc:InvoiceTypeCode'] = {'_text': None}
        if self._is_document(vals, 'invoice') and invoice._is_downpayment():
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 386
        else:
            super()._ubl_add_invoice_type_code_node(vals)

    def _ubl_add_credit_note_type_code_node(self, vals):
        # Override account_edi_ubl: [BR-FR-04] Downpayment code for credit note is 503
        invoice = vals['invoice']
        vals['document_node']['cbc:CreditNoteTypeCode'] = {'_text': None}
        if self._is_document(vals, 'credit_note') and invoice._is_downpayment():
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 503
        else:
            super()._ubl_add_credit_note_type_code_node(vals)

    def _ubl_get_partner_address_node(self, vals, partner):
        # EXTENDS account.edi.ubl
        node = super()._ubl_get_partner_address_node(vals, partner)
        node['cac:Country']['cbc:Name'] = None
        return node

    def _ubl_add_party_endpoint_id_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_endpoint_id_node(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id
        if commercial_partner.peppol_endpoint and commercial_partner.peppol_eas:
            vals['party_node']['cbc:EndpointID']['_text'] = commercial_partner.peppol_endpoint
            vals['party_node']['cbc:EndpointID']['schemeID'] = commercial_partner.peppol_eas

    def _ubl_add_party_tax_scheme_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_tax_scheme_nodes(vals)
        if self._need_party_tax_scheme_nodes(vals):
            self._ubl_add_party_tax_scheme_nodes_vat_gst(vals)

    def _ubl_add_party_identification_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_identification_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        id_type, party_id = commercial_partner._l10n_fr_pdp_get_base_identifier()
        if id_type == 'siret':
            party_id_scheme = "0009"
        else:  # id_type == 'siren'
            party_id_scheme = "0002"
        # [UBL-SR-16] Buyer identifier shall occur maximum once
        vals['party_node']['cac:PartyIdentification'] = {
            'cbc:ID': {'_text': party_id, 'schemeID': party_id_scheme},
        }

    def _ubl_add_party_legal_entity_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_party_legal_entity_nodes(vals)
        partner = vals['party_vals']['partner']
        commercial_partner = partner.commercial_partner_id

        vals['party_node']['cac:PartyLegalEntity'] = {
            'cbc:RegistrationName': {'_text': commercial_partner.name},
            'cbc:CompanyID': {
                '_text': commercial_partner._l10n_fr_pdp_get_siren(),
                'schemeID': '0002',
            },
        }

        # B2G
        customer = vals['customer'].commercial_partner_id
        if not self._pdp_needs_b2g_fields(customer):
            return

        id_type, party_id = commercial_partner._l10n_fr_pdp_get_base_identifier()
        if id_type == 'siret':
            vals['party_node']['cac:PartyLegalEntity'] = [{
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {
                    '_text': party_id,
                    'schemeID': '0009',
                },
            }]

    def _ubl_add_line_price_node(self, vals, in_foreign_currency=True):
        # OVERRIDE
        line_node = vals['line_node']
        base_line = vals['line_vals']['base_line']
        suffix = '_currency' if in_foreign_currency else ''
        currency = base_line['currency_id'] if in_foreign_currency else vals['company_currency']
        price_amount = base_line['tax_details'][f'raw_gross_price_unit{suffix}']

        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': FloatFmt(price_amount, min_dp=1, max_dp=6),
                'currencyID': currency.name,
            },
        }

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_ubl_invoice_add_prepaid_amount(self, collected_values):
        # imported invoice is a final invoice following downpayments.
        # We assume all billing references are references to downpayments.
        invoice = collected_values['invoice']
        currency = collected_values['currency_values']['currency']
        tree = collected_values['tree']
        if tree.findtext('./{*}ProfileID') in ('B4', 'S4', 'M4'):
            prepaid_amount = float(tree.findtext('./{*}LegalMonetaryTotal/{*}PrepaidAmount') or 0)
            collected_values['prepaid_amount'] = prepaid_amount
            if not invoice.currency_id.is_zero(prepaid_amount):
                downpayments_names = tree.findall('./{*}BillingReference/{*}InvoiceDocumentReference/{*}ID')
                downpayments = self.env['account.move'].search([('payment_reference', 'in', [downpayment.text for downpayment in downpayments_names])])

                downpayment_lines = self.env['account.move.line']
                for downpayment in downpayments:
                    downpayment_lines |= downpayment.invoice_line_ids.copy({'quantity': -1 if downpayment.move_type == 'in_invoice' else 1})
                collected_values['downpayment_lines'] = downpayment_lines

                # logging
                formatted_amount = formatLang(self.env, prepaid_amount, currency_obj=currency)
                collected_values['logs'].append(_("A downpayment of %s was detected.", formatted_amount))
                for downpayment_name in downpayments_names:
                    if downpayment_name.text not in downpayments.mapped('payment_reference'):
                        collected_values['logs'].append(_("Downpayment %s not found. Imported amounts will probably be incorrect.", downpayment_name.text))
        super()._import_ubl_invoice_add_prepaid_amount(collected_values)

    def _import_ubl_invoice_fix_untaxed_amount(self, collected_values):
        # Downpayments may be reported as a prepaid amount.
        # In this case, the final invoice untaxed amount, tax amount and total amount
        # correspond to the amounts without any downpayments made.
        # We need to add the downpayment lines as negative lines in the final invoice
        # because we already imported and accounted for the downpayments.
        super()._import_ubl_invoice_fix_untaxed_amount(collected_values)
        invoice = collected_values['invoice']
        if downpayment_lines := collected_values.get('downpayment_lines'):
            container = {'records': invoice}
            with (
                invoice._check_balanced(container),
                invoice._disable_discount_precision(),
                invoice._sync_dynamic_lines(container),
            ):
                downpayment_lines.move_id = invoice.id

    def _import_invoice_ubl_cii(self, invoice, file_data, new=False):
        # EXTENDS account.edi.common
        return self._ubl_import_invoice(invoice, file_data, new=new)

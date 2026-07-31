from odoo import models
from odoo.tools import html2plaintext

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

PDP_CUSTOMIZATION_ID = 'urn:cen.eu:en16931:2017'  # Not accepted by SuperPDP due to missing validator

PAID_STATES = frozenset({'in_payment', 'paid'})


class AccountEdiXmlUbl21Fr(models.AbstractModel):
    _name = "account.edi.xml.ubl_21_fr"
    _inherit = "account.edi.ubl_cen_en16931"
    _description = "France UBL 2.1 E-Invoicing Format"

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

    def _ubl_add_invoice_type_code_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_invoice_type_code_node(vals)
        if self._is_document(vals, 'invoice'):
            vals['document_node']['cbc:InvoiceTypeCode']['_text'] = 380

    def _ubl_add_credit_note_type_code_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_credit_note_type_code_node(vals)
        if self._is_document(vals, 'credit_note'):
            vals['document_node']['cbc:CreditNoteTypeCode']['_text'] = 381

    def _ubl_add_document_currency_code_node(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_document_currency_code_node(vals)
        vals['document_node']['cbc:DocumentCurrencyCode']['_text'] = vals['currency'].name

    def _ubl_add_invoice_header_nodes(self, vals):
        # EXTENDS account.edi.ubl
        super()._ubl_add_invoice_header_nodes(vals)

        invoice = vals['invoice']
        document_node = vals['document_node']

        # Les valeurs autorisées pour le Cadre (Mode de Facturation) sont:
        # B1 : Dépôt d'une facture de bien
        # S1 : Dépôt d'une facture de prestation de service
        # M1 : Dépôt d'une facture double (livraison de bien et services qui ne sont pas accessoires l'une de l'autre)
        # B2 : Dépôt d'une facture de bien déjà payée
        # S2 : Dépôt d'une facture de prestation de service déjà payée
        # M2 : Dépôt d'une facture double déjà payée
        # B4 : Dépôt d'une facture définitive (après acompte) de bien
        # S4 : Dépôt d'une facture définitive (après acompte) de service
        # M4 : Dépôt d'une facture définitive (après acompte) double
        # S5 : Dépôt par un sous-traitant d'une facture de prestation de service
        # S6 : Dépôt par un cotraitant d'une facture de prestation de service
        # B7 : Dépôt d'une facture de bien ayant fait l'objet d'un e-reporting (TVA déjà collectée)
        # S7 : Dépôt d'une facture de prestation de service ayant fait l'objet d'un e-reporting (TVA déjà collectée)

        tax_scopes = set(invoice.invoice_line_ids.tax_ids.mapped('tax_scope'))
        profile_scope = "B"
        if {'service', 'consu'}.issubset(tax_scopes):
            profile_scope = "M"
        elif 'service' in tax_scopes:
            profile_scope = "S"

        profile_number = "1"
        if invoice.payment_state in PAID_STATES:
            # Already paid
            profile_number = "2"
        elif not invoice._is_downpayment() and invoice.invoice_line_ids._get_downpayment_lines():
            # After downpayment
            profile_number = "4"

        profile_id = f"{profile_scope}{profile_number}"
        document_node.update({
            'cbc:CustomizationID': {'_text': PDP_CUSTOMIZATION_ID},
            'cbc:ProfileID': {'_text': profile_id},
        })

        # [BR-FR-05] Add mandatory notes with defaults if not already present
        # Initialize / Listify 'cbc:Note'
        existing_note = document_node.get('cbc:Note')
        if not existing_note or not isinstance(document_node.get('cbc:Note'), list):
            document_node['cbc:Note'] = [existing_note] if existing_note else []

        # Add the invoice narration, if any
        if invoice.narration:
            document_node['cbc:Note'].append({'_text': html2plaintext(invoice.narration)})

        # Add default notes
        for code, default_content in invoice._l10n_fr_pdp_get_default_notes().items():
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

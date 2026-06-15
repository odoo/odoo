from odoo import models

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

PDP_CUSTOMIZATION_ID = 'urn:cen.eu:en16931:2017'  # Not accepted by SuperPDP due to missing validator

PAID_STATES = frozenset({'in_payment', 'paid'})


class AccountEdiXmlUbl21Fr(models.AbstractModel):
    _name = "account.edi.xml.ubl_21_fr"
    _inherit = 'account.edi.xml.ubl_bis3'
    _description = "France UBL 2.1 E-Invoicing Format"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_21_fr.xml"

    def _export_invoice_constraints(self, invoice, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        constraints = super()._export_invoice_constraints(invoice, vals)

        for partner_type in ('supplier', 'customer'):
            partner = vals[partner_type]
            commercial_partner = partner.commercial_partner_id
            if commercial_partner.peppol_eas != '0225' or not commercial_partner.peppol_endpoint:
                constraints[f"ubl_21_fr_{partner_type}_pdp_identifier_required"] = self.env._("The following partner's PDP identifier is missing: %s", commercial_partner.display_name)
            id_type, id_value = commercial_partner._l10n_fr_pdp_get_base_identifier()
            if not id_type or not id_value:
                constraints[f"ubl_21_fr_{partner_type}_siret_required"] = self.env._("The following partner's SIREN or SIRET is missing: %s", commercial_partner.display_name)
            if not commercial_partner.vat or commercial_partner.vat == '/':
                constraints[f"ubl_21_fr_{partner_type}_vat_required"] = self.env._("The following partner's VAT is missing: %s", commercial_partner.display_name)

        if vals['document_type'] == 'credit_note' and not (invoice.reversed_entry_id.name or invoice.reversed_entry_id.invoice_date):
            constraints[f"ubl_21_fr_{partner_type}_refund_invoice_reference"] = self.env._("The original journal entry's name or issue date are missing: %s", vals['invoice'].name)

        return constraints

    def _add_invoice_header_nodes(self, document_node, vals):
        # EXTENDS account.edi.xml.ubl_bis3
        invoice = vals['invoice']
        super()._add_invoice_header_nodes(document_node, vals)

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
        # Add default notes
        for code, default_content in invoice._l10n_fr_pdp_get_default_notes().items():
            document_node['cbc:Note'].append({
                '_text': f"#{code}#{default_content}",
            })

        # Règles de gestion G1.52
        if vals['document_type'] == 'credit_note':
            document_node['cac:BillingReference'] = {
                'cac:InvoiceDocumentReference': {
                    'cbc:ID': {'_text': invoice.reversed_entry_id.name},
                    'cbc:IssueDate': {'_text': invoice.reversed_entry_id.invoice_date},
                }
            }

    def _ubl_add_party_identification_nodes(self, vals):
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
        # EXTENDS account.edi.xml.ubl_bis3
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
            'cac:AllowanceCharge': {
                "cbc:ChargeIndicator": [{
                    "_text": 'false',
                }],
                # Discount amount
                "cbc:Amount": [{
                    "_text": FloatFmt(0, min_dp=1, max_dp=6),
                    "currencyID": currency.name,
                }],
                # Pre-discount amount
                'cbc:BaseAmount': {
                    '_text': FloatFmt(price_amount, min_dp=1, max_dp=6),
                    'currencyID': currency.name,
                },
            }
        }

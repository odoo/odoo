from odoo import _, models

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
                constraints[f"ubl_21_fr_{partner_type}_pdp_identifier_required"] = _("The following partner's PDP identifier is missing: %s", commercial_partner.display_name)
            id_type, id_value = commercial_partner._l10n_fr_pdp_get_base_identifier()
            if not id_type or not id_value:
                constraints[f"ubl_21_fr_{partner_type}_siret_required"] = _("The following partner's SIREN or SIRET is missing: %s", commercial_partner.display_name)
            if not commercial_partner.vat or commercial_partner.vat == '/':
                constraints[f"ubl_21_fr_{partner_type}_vat_required"] = _("The following partner's VAT is missing: %s", commercial_partner.display_name)

        if vals['document_type'] == 'credit_note' and not (invoice.reversed_entry_id.name or invoice.reversed_entry_id.invoice_date):
            constraints[f"ubl_21_fr_{partner_type}_refund_invoice_reference"] = _("The original journal entry's name or issue date are missing: %s", vals['invoice'].name)

        return constraints

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)

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

        vals['vals'].update({
            'customization_id': PDP_CUSTOMIZATION_ID,
            'profile_id': f"{profile_scope}{profile_number}",
            # Règles de gestion G1.31
            'billing_reference_vals': {
               'id': invoice.reversed_entry_id.name,
               'issue_date': invoice.reversed_entry_id.invoice_date,
            },
        })

        return vals

    def _get_note_vals_list(self, invoice):
        # EXTENDS account.edi.xml.ubl_20
        note_vals = super()._get_note_vals_list(invoice)
        # [BR-FR-05] Add mandatory notes with defaults if not already present
        return note_vals + [
            {'note': f"#{code}#{default_content}"}
            for code, default_content in invoice._l10n_fr_pdp_get_default_notes().items()
        ]

    def _get_partner_party_identification_vals_list(self, partner):
        # OVERRIDE
        # [UBL-SR-16] Buyer identifier shall occur maximum once
        commercial_partner = partner.commercial_partner_id
        id_type, party_id = commercial_partner._l10n_fr_pdp_get_base_identifier()
        if id_type == 'siret':
            party_id_scheme = "0009"
        else:  # id_type == 'siren'
            party_id_scheme = "0002"
        return [{
            'id_attrs': {'schemeID': party_id_scheme},
            'id': party_id,
        }]

    def _get_partner_party_legal_entity_vals_list(self, partner):
        commercial_partner = partner.commercial_partner_id
        return [{
            'registration_name': commercial_partner.name,
            'company_id': commercial_partner._l10n_fr_pdp_get_siren(),
            'company_id_attrs': {'schemeID': '0002'},
        }]

    def _get_invoice_line_price_vals(self, line):
        price_vals = super()._get_invoice_line_price_vals(line)
        currency = price_vals['currency']
        price_vals['allowance_charge_vals_list'] = [{
            'charge_indicator': 'false',
            'currency_dp': price_vals['product_price_dp'],
            'currency_name': currency.name,
            'amount': 0,  # Discount amount
            'base_amount': price_vals['price_amount'],  # Pre-discount amount
        }]
        return price_vals

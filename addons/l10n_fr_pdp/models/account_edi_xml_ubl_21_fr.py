from odoo import _, api, models

PDP_CUSTOMIZATION_ID = 'urn:cen.eu:en16931:2017'  # Not accepted by SuperPDP due to missing validator

CPRO_CUSTOMIZATION_ID = 'urn:cen.eu:en16931:2017#conformant#urn.cpro.gouv.fr:1p0:extended-ctc-fr'
CPRO_INVOICE_IDENTIFIER = f'busdox-docid-qns::urn:oasis:names:specification:ubl:schema:xsd:Invoice-2::Invoice##{CPRO_CUSTOMIZATION_ID}::2.1'

PAID_STATES = frozenset({'in_payment', 'paid'})


class AccountEdiXmlUbl21Fr(models.AbstractModel):
    _name = "account.edi.xml.ubl_21_fr"
    _inherit = 'account.edi.xml.ubl_bis3'
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

        customer = vals['customer'].commercial_partner_id
        if self._pdp_is_b2g(customer) and not self._pdp_can_invoice_b2g(customer):
            cpro_module_name = self.env['ir.module.module'].sudo()._get('l10n_fr_facturx_chorus_pro').display_name
            constraints["ubl_21_fr_cpro_module_missing"] = self.env._("This partner is behind Chorus PRO. Please install the module '%s'", cpro_module_name)

        return constraints

    def _export_invoice_vals(self, invoice):
        # EXTENDS account.edi.xml.ubl_bis3
        vals = super()._export_invoice_vals(invoice)
        customer = vals['customer'].commercial_partner_id
        b2g = self._pdp_needs_b2g_fields(customer)

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
            'customization_id': CPRO_CUSTOMIZATION_ID if b2g else PDP_CUSTOMIZATION_ID,
            'profile_id': f"{profile_scope}{profile_number}",
            # Règles de gestion G1.31
            'billing_reference_vals': {
               'id': invoice.reversed_entry_id.name,
               'issue_date': invoice.reversed_entry_id.invoice_date,
            },
        })

        # B2G
        if not b2g:
            return vals

        if invoice.buyer_reference:
            vals['vals']['buyer_reference'] = invoice.buyer_reference

        if invoice.purchase_order_reference:
            vals['vals']['order_reference'] = invoice.purchase_order_reference

        for role in ('supplier', 'customer'):
            party_vals = vals['vals'][f'accounting_{role}_party_vals']['party_vals']
            partner = vals[role].commercial_partner_id
            id_type, party_id = partner._l10n_fr_pdp_get_base_identifier()
            if id_type == 'siret':
                for party_vals in party_vals['party_legal_entity_vals']:
                    party_vals.update({
                        'company_id': party_id,
                        'company_id_attrs': {'schemeID': '0009'},
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

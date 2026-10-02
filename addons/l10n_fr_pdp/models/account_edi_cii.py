from odoo import models


class L10nFRAccountEdiCii(models.AbstractModel):
    _inherit = "account.edi.cii"

    def _cii_add_exchanged_document_context_node(self, vals):
        node = vals['document_node'].setdefault('rsm:ExchangedDocumentContext', {})
        if vals['company']._get_peppol_proxy_type() == 'pdp':
            node['ram:BusinessProcessSpecifiedDocumentContextParameter'] = {
                'ram:ID': {'_text': self._l10n_fr_pdp_get_profile_id(vals)},
            }
        super()._cii_add_exchanged_document_context_node(vals)

    def _cii_add_exchanged_document_node(self, vals):
        super()._cii_add_exchanged_document_node(vals)
        invoice = vals['invoice']
        if invoice._l10n_fr_pdp_is_document_type_262():
            vals['document_node']['rsm:ExchangedDocument']['ram:TypeCode']['_text'] = '262'

    def _cii_get_applicable_header_trade_agreement_node(self, vals):
        node = super()._cii_get_applicable_header_trade_agreement_node(vals)
        invoice = vals['invoice']
        if invoice._l10n_fr_pdp_is_document_type_262():
            contract_ref = invoice._l10n_fr_pdp_get_contract_reference()
            node['ram:ContractReferencedDocument'] = {
                'ram:IssuerAssignedID': {'_text': contract_ref},
            }
        return node

    def _cii_get_billing_specified_period_node(self, vals):
        invoice = vals['invoice']
        if invoice._l10n_fr_pdp_is_document_type_262():
            start, end = invoice._l10n_fr_pdp_get_invoicing_period()
            return {
                'ram:StartDateTime': self._cii_get_date_time_string_node(vals, start) if start else None,
                'ram:EndDateTime': self._cii_get_date_time_string_node(vals, end) if end else None,
            }
        return super()._cii_get_billing_specified_period_node(vals)

    def _cii_constraints(self, invoice, vals):
        constraints = super()._cii_constraints(invoice, vals)
        self._l10n_fr_pdp_cii_check_narration(vals, constraints)
        self._l10n_fr_pdp_cii_check_peppol_fields(vals, constraints)
        if invoice._l10n_fr_pdp_is_document_type_262():
            if not invoice._l10n_fr_pdp_get_contract_reference():
                constraints['cii_262_contract'] = self.env._(
                    "A contract reference (BT-12) is required for a standalone commercial credit note (262).",
                )
            start, end = invoice._l10n_fr_pdp_get_invoicing_period()
            if not start or not end:
                constraints['cii_262_period'] = self.env._(
                    "An invoicing period (BG-14) is required for a standalone commercial credit note (262).",
                )
        return constraints

    def _l10n_fr_pdp_cii_check_narration(self, vals, constraints):
        if vals['company']._get_peppol_proxy_type() == 'pdp':
            constraints['narration'] = self._check_required_fields(
                    vals['invoice'], 'narration'
                )

    def _l10n_fr_pdp_cii_check_peppol_fields(self, vals, constraints):
        """
        [BR-FR-12] - Since the electronic invoice must be sent and is awaiting
        lifecycle status updates in return, the Buyer's email address (BT-34) is
        REQUIRED.
        [BR-FR-13] - Since the electronic invoice must be sent and is awaiting
        lifecycle status updates in return, the Seller's email address (BT-34) is
        REQUIRED.
        """
        if vals['company']._get_peppol_proxy_type() == 'pdp':
            constraints.update({
                'buyer_peppol_eas': self._check_required_fields(
                    vals['customer'].commercial_partner_id, 'peppol_eas'
                ),
                'buyer_peppol_endpoint': self._check_required_fields(
                    vals['customer'].commercial_partner_id, 'peppol_endpoint'
                ),
                'seller_peppol_eas': self._check_required_fields(
                    vals['supplier'].commercial_partner_id, 'peppol_eas'
                ),
                'seller_peppol_endpoint': self._check_required_fields(
                    vals['supplier'].commercial_partner_id, 'peppol_endpoint'
                ),
            })

from odoo import models

from odoo.addons.account_edi_ubl_cii.models.account_edi_cii import DEFAULT_CII_DATE_FORMAT


class L10nFRAccountEdiCii(models.AbstractModel):
    _inherit = "account.edi.cii"

    def _cii_add_exchanged_document_context_node(self, vals):
        node = vals['document_node'].setdefault('rsm:ExchangedDocumentContext', {})
        if vals['company']._get_peppol_proxy_type() == 'pdp':
            node['ram:BusinessProcessSpecifiedDocumentContextParameter'] = {
                'ram:ID': {'_text': self._l10n_fr_pdp_get_profile_id(vals)},
            }
        super()._cii_add_exchanged_document_context_node(vals)

    def _cii_get_included_supply_chain_trade_line_item_node(self, vals, line_idx, base_line):
        # EXTENDS account_edi_ubl_cii
        node = super()._cii_get_included_supply_chain_trade_line_item_node(vals, line_idx, base_line)
        if vals['company']._get_peppol_proxy_type() == 'pdp':
            # Order, delivery order and delivery address per line (multi-order / multi-delivery invoices).
            trade_references = self._get_line_trade_references(base_line)
            node['ram:SpecifiedLineTradeAgreement']['ram:BuyerOrderReferencedDocument'] = self._l10n_fr_pdp_cii_get_line_buyer_order_referenced_document_node(trade_references)
            delivery_node = node['ram:SpecifiedLineTradeDelivery']
            delivery_node['ram:ShipToTradeParty'] = self._l10n_fr_pdp_cii_get_line_ship_to_trade_party_node(vals, trade_references)
            delivery_node['ram:DespatchAdviceReferencedDocument'] = self._l10n_fr_pdp_cii_get_line_despatch_advice_referenced_document_node(trade_references)
        return node

    def _l10n_fr_pdp_cii_get_line_buyer_order_referenced_document_node(self, trade_references):
        if not trade_references.get('order_ref'):
            return None
        return {
            'ram:IssuerAssignedID': {'_text': trade_references['order_ref']},
        }

    def _l10n_fr_pdp_cii_get_line_ship_to_trade_party_node(self, vals, trade_references):
        # Only when the line is delivered elsewhere than the invoice's delivery address.
        ship_to = trade_references.get('ship_to')
        if not ship_to or ship_to == vals['partner_shipping']:
            return None
        node = self._cii_get_ship_to_trade_party_node({**vals, 'partner_shipping': ship_to})
        node['ram:DefinedTradeContact'] = None
        if ship_to.state_id:
            node['ram:PostalTradeAddress']['ram:CountrySubDivisionName'] = {'_text': ship_to.state_id.name}
        return node

    def _l10n_fr_pdp_cii_get_line_despatch_advice_referenced_document_node(self, trade_references):
        if not trade_references.get('despatch_ref'):
            return None
        return {
            'ram:IssuerAssignedID': {'_text': trade_references['despatch_ref']},
            'ram:LineID': {'_text': trade_references.get('despatch_line_ref')},
        }

    def _cii_add_exchanged_document_node(self, vals):
        invoice = vals['invoice']
        if invoice._is_downpayment() and vals['company']._get_peppol_proxy_type() == 'pdp':
            vals['document_node']['rsm:ExchangedDocument'] = {
                'ram:ID': {'_text': invoice.name},
                'ram:TypeCode': {'_text': '386' if invoice.move_type == 'out_invoice' else '503'},
                'ram:IssueDateTime': self._cii_get_date_time_string_node(vals, invoice.invoice_date),
                'ram:IncludedNote': self._cii_get_included_note_node(vals),
            }
        else:
            super()._cii_add_exchanged_document_node(vals)

    def _cii_get_applicable_header_trade_settlement_node(self, vals):
        invoice = vals['invoice']
        res = super()._cii_get_applicable_header_trade_settlement_node(vals)
        if self._l10n_fr_pdp_get_profile_id(vals) in ('B4', 'S4', 'M4') and vals['company']._get_peppol_proxy_type() == 'pdp':
            downpayment_moves = invoice.invoice_line_ids._get_downpayment_lines().move_id.filtered(lambda m: m != invoice)
            res['ram:InvoiceReferencedDocument'] = []
            for downpayment_move in downpayment_moves:
                res['ram:InvoiceReferencedDocument'].append({
                        'ram:IssuerAssignedID': {'_text': downpayment_move.name},
                        'ram:FormattedIssueDateTime': {
                            'qdt:DateTimeString': {
                                '_text': downpayment_move.invoice_date.strftime(DEFAULT_CII_DATE_FORMAT),
                                'format': "102",
                            },
                        },
                        'ram:TypeCode': {'_text': 386 if downpayment_move.move_type == 'out_invoice' else 503},  # downpayment invoice or downpayment credit note
                    },
                )
        return res

    def _cii_constraints(self, invoice, vals):
        constraints = super()._cii_constraints(invoice, vals)
        self._l10n_fr_pdp_cii_check_narration(vals, constraints)
        self._l10n_fr_pdp_cii_check_peppol_fields(vals, constraints)
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

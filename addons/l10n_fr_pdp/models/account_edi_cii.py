from odoo import _, models
from odoo.tools.misc import formatLang

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
                    vals['customer'].commercial_partner_id, 'routing_scheme'
                ),
                'buyer_peppol_endpoint': self._check_required_fields(
                    vals['customer'].commercial_partner_id, 'routing_endpoint'
                ),
                'seller_peppol_eas': self._check_required_fields(
                    vals['supplier'].commercial_partner_id, 'routing_scheme'
                ),
                'seller_peppol_endpoint': self._check_required_fields(
                    vals['supplier'].commercial_partner_id, 'routing_endpoint'
                ),
            })

    def _import_cii_invoice_add_prepaid_amount(self, collected_values):
        # imported invoice is a final invoice following downpayments.
        # We assume all billing references are references to downpayments.
        invoice = collected_values['invoice']
        currency = collected_values['currency_values']['currency']
        tree = collected_values['tree']
        if tree.findtext('./{*}ExchangedDocumentContext/{*}BusinessProcessSpecifiedDocumentContextParameter/{*}ID') in ('B4', 'S4', 'M4'):
            prepaid_amount = float(tree.findtext('./{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}TotalPrepaidAmount') or 0)
            collected_values['prepaid_amount'] = prepaid_amount
            if not invoice.currency_id.is_zero(prepaid_amount):
                downpayments_names = tree.findall('./{*}SupplyChainTradeTransaction/{*}ApplicableHeaderTradeSettlement/{*}InvoiceReferencedDocument/{*}IssuerAssignedID')
                # groups downpayments by ref to avoid a downpayment being duplicated in the db being substracted multiple times
                grouped_downpayments = self.env['account.move'].search([
                    ('ref', 'in', [downpayment.text for downpayment in downpayments_names]),
                    ('company_id', '=', collected_values['company'].id),
                    ('commercial_partner_id', '=', collected_values['customer_values']['customer'].id),
                ]).grouped('ref')
                downpayment_lines = self.env['account.move.line']
                for downpayments in grouped_downpayments.values():
                    downpayment = downpayments[0]
                    for line in downpayment.invoice_line_ids:
                        downpayment_lines |= line.copy({'quantity': -line.quantity if downpayment.move_type == 'in_invoice' else line.quantity})
                collected_values['downpayment_lines'] = downpayment_lines

                # logging
                formatted_amount = formatLang(self.env, prepaid_amount, currency_obj=currency)
                collected_values['logs'].append(_("A downpayment of %s was detected.", formatted_amount))
                for downpayment_name in downpayments_names:
                    if downpayment_name.text not in grouped_downpayments:
                        collected_values['logs'].append(_("Downpayment %s not found. Imported amounts will probably be incorrect.", downpayment_name.text))
        super()._import_cii_invoice_add_prepaid_amount(collected_values)

    def _import_cii_invoice_fix_untaxed_amount(self, collected_values):
        # Downpayments may be reported as a prepaid amount.
        # In this case, the final invoice untaxed amount, tax amount and total amount
        # correspond to the amounts without any downpayments made.
        # We need to add the downpayment lines as negative lines in the final invoice
        # because we already imported and accounted for the downpayments.
        super()._import_cii_invoice_fix_untaxed_amount(collected_values)
        invoice = collected_values['invoice']
        if downpayment_lines := collected_values.get('downpayment_lines'):
            container = {'records': invoice}
            with (
                invoice._check_balanced(container),
                invoice._disable_discount_precision(),
                invoice._sync_dynamic_lines(container),
            ):
                downpayment_lines.move_id = invoice.id

from odoo import _, models
from odoo.tools.misc import formatLang


class AccountEdiXmlCII(models.AbstractModel):
    _inherit = "account.edi.xml.cii"

    def _get_exchanged_document_vals(self, invoice):
        # Extend `account_edi_xml_cii` to add mandatory default notes [BR-FR-05]
        result = super()._get_exchanged_document_vals(invoice)

        result['included_note_list'].extend([
            {
                'subject_code': code,
                'content': content,
            } for code, content in invoice._l10n_fr_pdp_get_default_notes().items()
        ])

        return result

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _cii_get_included_note_node(self, vals):
        # EXTENDS account.edi.cii
        nodes = super()._cii_get_included_note_node(vals)

        # [BR-FR-MAP-18] EN16931 caps the Note (BT-22) to 1024 characters.
        for node in nodes:
            if (
                (note_node := node['ram:Content'])
                and isinstance(note_node['_text'], str)
            ):
                note_node['_text'] = note_node['_text'][:1024]

        return nodes

    def _cii_get_line_specified_trade_product_node(self, vals, base_line):
        # EXTENDS account.edi.cii
        node = super()._cii_get_line_specified_trade_product_node(vals, base_line)

        # [BR-FR-MAP-17] EN16931 caps the Item name (BT-153) to 255 characters.
        if (
            (item_name_node := node.get('ram:Name'))
            and isinstance(item_name_node['_text'], str)
        ):
            item_name_node['_text'] = item_name_node['_text'][:255]

        return node

    def _cii_get_postal_trade_address_node(self, vals, address_values):
        # EXTENDS account.edi.cii
        node = super()._cii_get_postal_trade_address_node(vals, address_values)

        # [BR-FR-MAP-17/BR-FR-MAP-19] EN16931 caps these address lines to 255 characters (postal code: 10).
        for field in ('ram:LineOne', 'ram:LineTwo', 'ram:CityName'):
            if node.get(field) and isinstance(node[field]['_text'], str):
                node[field]['_text'] = node[field]['_text'][:255]

        if (
            (postcode_node := node['ram:PostcodeCode'])
            and isinstance(postcode_node['_text'], str)
        ):
            postcode_node['_text'] = postcode_node['_text'][:10]

        return node

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _get_import_document_amount_sign(self, tree):
        move_type, sign = super()._get_import_document_amount_sign(tree)
        if move_type:
            return move_type, sign
        move_type_code = tree.find('.//{*}ExchangedDocument/{*}TypeCode')
        if move_type_code is None:
            return None, None
        if move_type_code.text == '503':
            return 'refund', 1
        if move_type_code.text == '386':
            amount_node = tree.find('.//{*}SpecifiedTradeSettlementHeaderMonetarySummation/{*}GrandTotalAmount')
            if amount_node is not None and float(amount_node.text) < 0:
                return 'refund', -1
            return 'invoice', 1
        return None, None

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

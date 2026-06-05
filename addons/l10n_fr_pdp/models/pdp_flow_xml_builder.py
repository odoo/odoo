from collections import defaultdict
from lxml import etree
import base64

from odoo import api, fields, models
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.l10n_fr_pdp.utils import drom_com_territories
from odoo.tools import float_is_zero, float_round, frozendict, html2plaintext, ormcache


VALID_TAX_CODES = {
    'S',   # Standard VAT rate (Taux de TVA standard)
    'E',   # VAT exempt (Exonéré de TVA)
    'AE',  # VAT reverse charge (Autoliquidation de TVA)
    'K',   # VAT exemption for intra-Community supply (Exonération pour cause de livraison intracommunautaire)
    'G',   # VAT exemption for exports outside the EU (Exonération de TVA pour Export hors UE)
    'O',   # Outside the scope of VAT (Hors du périmètre d'application de la TVA)
    'Z',   # Zero VAT rate (see G1.47) (Taux de TVA égal à 0 (cf. G1.47))
}


class PdpFlow10XMLBuilder(models.AbstractModel):
    """Build Flow 10 XML for a flow"""
    _name = 'pdp.flow.10.xml.builder'
    _inherit = 'account.edi.common'
    _description = 'Flow 10 XML Builder'

    @api.model
    def _build_payload(self, flow, valid_moves):
        if not valid_moves:
            return False

        document = {'_tag': 'Report'}

        self._add_report_header(document, flow)  # TB-1

        if flow.report_type == 'transaction':
            self._add_transactions(document, flow, valid_moves)  # TB-2
        else:
            self._add_payments(document, flow, valid_moves)  # TB-3

        xml = dict_to_xml(
            node=document,
            nsmap={'xsi': 'http://www.w3.org/2001/XMLSchema-instance'},
        )
        payload = base64.b64encode(
            etree.tostring(xml, pretty_print=True, xml_declaration=True, encoding='UTF-8'),
        )
        return payload

    @api.model
    def _add_report_header(self, document, flow):
        document['ReportDocument'] = {
            'Id': {'_text': flow._get_tracking_id()},
            'IssueDateTime': {
                'DateTimeString': {
                    '_text': fields.Datetime.now().strftime('%Y%m%d%H%M%S'),
                },
            },
            'TypeCode': {'_text': 'RE' if flow.transmission_type == 'rectificative' else 'IN'},
            'Sender': {
                'Id': {'schemeId': '0238', '_text': '2728'},
                'Name': {'_text': 'PDP_2728'},
                'RoleCode': {'_text': 'WK'},
                'URIUniversalCommunication': {
                    'URIID': {'_text': 'pdp@odoo.com'},
                },
            },
            'Issuer': {
                'Id': {'schemeId': '0002', '_text': flow.company_id.partner_id._l10n_fr_pdp_get_siren()},
                'Name': {'_text': flow.company_id.name[:99]},
                'RoleCode': {'_text':  'BY' if flow.operation_type == 'purchase' else 'SE'},
                **({'URIUniversalCommunication': {
                    'URIID': {'_text': flow.company_id.email[:100]},
                }} if flow.company_id.email else {}),
            },
        }

    @api.model
    def _split_moves_by_transaction_type(self, flow, moves):
        if flow.operation_type == 'purchase':
            return self.env['account.move'], moves  # no VAT to report on b2c purchases
        b2c_moves = self.env['account.move']
        b2bi_moves = self.env['account.move']
        for move in moves:
            transaction_type = move._l10n_fr_pdp_get_transaction_type()
            if transaction_type == 'b2c':
                b2c_moves += move
            elif transaction_type == 'b2bi':
                b2bi_moves += move
        return b2c_moves, b2bi_moves

    @api.model
    def _add_payments(self, document, flow, moves):
        """ This method adds payment nodes to document. Per invoice for b2bi payments and
            agregated for b2c payments.
        """
        def get_payment_node(date, subtotals, currency_code, transaction=None):
            node = {
                **({
                    'InvoiceID': {'_text': transaction.name},
                    'IssueDate': {'_text': self._format_date(transaction.date)},
                } if transaction else {}),
                'Payment': {
                    'Date': {'_text': self._format_date(date)},
                    'SubTotals': [],
                }
            }
            for tax_subtotal in subtotals:
                node['Payment']['SubTotals'].append({
                    'TaxPercent': {'_text': tax_subtotal['tax'].amount},
                    'CurrencyCode': {'_text': currency_code},
                    'Amount': {'_text': float_round(tax_subtotal['tax_amount'], 6)},  # G1.16
                })
            return node

        matched_transactions_map = {'b2c': defaultdict(set), 'b2bi': defaultdict(set)}
        for payment in moves:
            transaction_type = payment._l10n_fr_pdp_get_transaction_type()
            for matched in payment._l10n_fr_pdp_get_matched_transactions():
                matched_transactions_map[transaction_type][matched].add(payment)

        invoices = []
        transactions = []
        payments_aggregates = defaultdict(lambda: defaultdict(float))

        for transaction_type, matched_map in matched_transactions_map.items():
            for transaction, payments in matched_map.items():
                summary = self._get_payments_summary(transaction, payments)  # {payment: (subtotals, transaction)}
                for payment, (subtotals, transaction) in summary.items():
                    if transaction_type == 'b2bi':
                        invoices.append(
                            get_payment_node(payment.date, subtotals, payment.currency_id.name, transaction)
                        )
                    else:
                        for subtotal in subtotals:
                            date_currency = frozendict({'date': payment.date, 'currency_name': payment.currency_id.name})
                            payments_aggregates[date_currency][subtotal['tax']] += subtotal['tax_amount']

        for payment_info, subtotals in payments_aggregates.items():
            date, currency_code = payment_info['date'], payment_info['currency_name']
            subtotals = [{'tax': tax, 'tax_amount': amount} for tax, amount in subtotals.items()]
            transactions.append(
                get_payment_node(date, subtotals, currency_code)
            )

        if invoices or transactions:
            document['PaymentsReport'] = {
                'ReportPeriod': {
                    'StartDate': {'_text': self._format_date(flow.period_start)},
                    'EndDate': {'_text': self._format_date(flow.period_end)},
                },
                'Invoice': invoices,
                'Transactions': transactions,
            }

    @api.model
    def _get_payments_summary(self, transaction, payments):
        tax_summary = self._get_tax_summary(
            transaction.line_ids,
            line_validation_function=(
                None if transaction._is_downpayment()
                else lambda line: any(tax.tax_exigibility == 'on_payment' for tax in line.tax_ids)
            ),
        )
        move_amount_total = transaction.amount_total
        summary = {}
        for payment in payments:
            subtotals = []
            reconciled_aml = transaction._get_reconciled_amls().filtered(lambda aml: aml.move_id == payment)
            partial_amount = abs(reconciled_aml.balance)
            partial_to_move_ratio = partial_amount / move_amount_total if move_amount_total else 0
            for tax, subtotal in tax_summary['subtotals'].items():
                subtotals.append({
                    'tax': tax,
                    'tax_amount': (subtotal['tax_amount'] + subtotal['taxable_amount']) * partial_to_move_ratio,
                })
            summary[payment] = (subtotals, transaction)

        return summary

    @api.model
    def _is_payment_partial_aml(self, aml):
        """Return True when a reconciled AML corresponds to an actual payment."""
        return bool(aml and (aml.move_id.origin_payment_id or aml.move_id.statement_line_id))

    @api.model
    def _add_transactions(self, document, flow, moves):
        b2c_moves, b2bi_moves = self._split_moves_by_transaction_type(flow, moves)

        b2bi_invoices = self._get_b2bi_transaction_nodes(flow, b2bi_moves)
        b2c_agregates = self._get_b2c_transaction_nodes(b2c_moves)

        if b2bi_invoices or b2c_agregates:
            document['TransactionsReport'] = {
                'ReportPeriod': {
                    'StartDate': {'_text': self._format_date(flow.period_start)},
                    'EndDate': {'_text': self._format_date(flow.period_end)},
                },
                'Invoice': b2bi_invoices,
                'Transactions': b2c_agregates,
            }

    @api.model
    def _get_b2bi_transaction_nodes(self, flow, moves):
        nodes = []
        for move in moves:
            is_purchase = move.is_purchase_document(include_receipts=False)
            seller = move.commercial_partner_id if is_purchase else move.company_id.partner_id
            buyer = move.company_id.partner_id if is_purchase else move.commercial_partner_id
            invoice_node = {
                'ID': {'_text': move.name},
                'IssueDate': {'_text': self._format_date(move.date)},
                'TypeCode': {'_text': self._get_move_typecode(move)},
                'CurrencyCode': {'_text': move.currency_id.name},
                'DueDate': {'_text': self._format_date(move.invoice_date_due or move.date)},
            }

            self._invoice_add_due_date_type_code(invoice_node, move)
            self._invoice_add_notes(invoice_node, move)
            self._invoice_add_business_process(invoice_node, move)
            self._invoice_add_referenced_documents(invoice_node, move)
            self._invoice_add_partner_vals(invoice_node, seller, 'Seller')
            self._invoice_add_partner_vals(invoice_node, buyer, 'Buyer')
            self._invoice_add_seller_tax_representative(invoice_node, move)
            self._invoice_add_delivery_vals(invoice_node, move)
            self._invoice_add_invoice_period(invoice_node, move, flow)
            self._invoice_add_allowance_charges(invoice_node, move, seller, buyer)
            self._invoice_add_monetary_total(invoice_node, move)
            self._invoice_add_tax_sub_total(invoice_node, move, seller, buyer)
            self._invoice_add_lines(invoice_node, move)

            nodes.append(invoice_node)
        return nodes

    @api.model
    def _get_b2c_transaction_nodes(self, moves):
        nodes = []
        summary = self._get_tax_summary(
            move_lines=moves.line_ids,
            agregation_function=lambda line: frozendict({
                'date': line.date,
                'currency_id': line.currency_id,
                'tax_due_date_type_code': self._get_move_tax_data(line.move_id)['tax_due_date_type_code'],
                'category_code': self._get_line_category_code(line),
            }),
        )
        for agregate, taxes in summary.items():
            nodes.append({
                'Date': {'_text': self._format_date(agregate['date'])},
                'TransactionsCurrency': {'_text': agregate['currency_id'].name},
                'TaxDueDateTypeCode': {'_text': agregate['tax_due_date_type_code']},
                'CategoryCode': {'_text': agregate['category_code']},
                'TaxExclusiveAmount': {'_text': float_round(taxes['taxable_amount_total'], 2)},  # G1.14
                'TaxTotal': {'_text': float_round(taxes['tax_total'], 2)},  # G1.14
                'TaxSubtotal': [{
                    'TaxPercent': {'_text': tax.amount if tax else 0},
                    'TaxableAmount': {'_text': float_round(subtotal['taxable_amount'], 2)},  # G1.14
                    'TaxTotal': {'_text': float_round(subtotal['tax_amount'], 2)},  # G1.14
                } for tax, subtotal in taxes['subtotals'].items()],
            })
        return nodes

    @api.model
    def _invoice_add_due_date_type_code(self, invoice, move):
        tax_due_date_type_code = self._get_move_tax_data(move)['tax_due_date_type_code']
        if tax_due_date_type_code:
            invoice['TaxDueDateTypeCode'] = {'_text': tax_due_date_type_code}

    @api.model
    def _get_line_category_code(self, line):
        # TODO: ADD TMA1 Margin scheme when applicable, add field on tax ??
        if all(float_is_zero(tax.amount, tax.fields_get('amount')['amount']['digits'][1]) for tax in line.tax_ids):
            return 'TNT1'
        if any(tax.tax_scope == 'service' for tax in line.tax_ids):
            return 'TPS1'
        return 'TLB1'  # 'consu'

    @api.model
    def _invoice_add_notes(self, invoice, move):
        if move.narration:
            invoice['IncludedNote'] = {
                'Subject': {'_text': 'AAB'},
                'Content':  {'_text': html2plaintext(move.narration).strip()},
            }

    @api.model
    @ormcache('move.id')
    def _get_move_tax_data(self, move):
        scopes = set()
        tax_exigibility_on_invoice = False
        move_is_downpayment = move._is_downpayment()
        down_payment_type = '2' if move_is_downpayment and move.payment_state in {'paid', 'reversed'} else '1'
        for line in move.invoice_line_ids:
            if line.display_type != 'product':
                continue

            if any(tax.tax_scope == 'service' for tax in line.tax_ids):
                scopes.add('S')
            elif any(tax.tax_scope == 'consu' for tax in line.tax_ids):
                scopes.add('B')
            if move_is_downpayment and not line.is_downpayment:
                down_payment_type = '4'
            if not tax_exigibility_on_invoice and any(tax.tax_exigibility in {None, 'on_invoice'} for tax in line.tax_ids):
                tax_exigibility_on_invoice = True

        scope = 'M' if len(scopes) == 2 else next(iter(scopes), 'B')  # B = goods (default), S = services, M = mixed.
        tax_due_date_type_code = '5' if scope == 'S' and tax_exigibility_on_invoice else None  # Should only be '5' when invoice is service (or mixed ?) and some services are subject to VAT invoice date.
        return {
            'scope': scope,
            'down_payment_type': down_payment_type,
            'tax_due_date_type_code': tax_due_date_type_code,
        }

    @api.model
    def _invoice_add_business_process(self, invoice, move):
        '''Determine billing framework ID (TT-28) from invoice'''
        move_data = self._get_move_tax_data(move)
        scope = move_data['scope']
        down_payment_type = move_data['down_payment_type']
        invoice['BusinessProcess'] = {
            'ID': {'_text': f'{scope}{down_payment_type}'},
            'TypeID': {'_text': 'urn.cpro.gouv.fr:1p0:ereporting'},
        }

    @api.model
    def _invoice_add_referenced_documents(self, invoice, move):
        invoice['ReferencedDocument'] = [{
            'ID': {'_text': ref_doc.name},
            'IssueDate': {'_text': self._format_date(ref_doc.date)}
        } for ref_doc in move._l10n_fr_pdp_get_referenced_documents()]

    @api.model
    def _invoice_add_partner_vals(self, invoice, partner, tag):
        # Country codes for DROM-COM territories are mapped to 'FR' for PPF transmission
        mapped_country_code = drom_com_territories.map_country_code_for_ppf(partner.country_id.code)
        # Check for specific identifier schemes (RIDET, TAHITI, etc.)
        specific_scheme = drom_com_territories.get_specific_identifier_scheme(partner.country_id.code)

        # Determine company scheme and ID
        if specific_scheme and partner.ref:
            # Use specific identifier for territories like NC (RIDET), PF (TAHITI), WF
            company_scheme = specific_scheme['qualifier']
            company_id = partner.ref
        elif siren := partner._l10n_fr_pdp_get_siren():
            # Standard French SIREN
            company_scheme = '0002'
            company_id = siren
        elif len(partner.vat) > 1:
            # VAT scheme
            company_scheme = '0223'
            company_id = partner.vat
        else:
            company_scheme = False
            company_id = partner.ref or ''

        partner_vals = {
            'CompanyId': {
                '_text': company_id,
                'schemeId': company_scheme,
            }
        }
        if len(partner.vat) > 1:
            partner_vals['TaxRegistrationId'] = {
                '_text': partner.vat,
                'qualifyingId': 'VAT',
            }
        if mapped_country_code:
            partner_vals['PostalAddress'] = {'CountryId': {
                '_text': mapped_country_code,
            }}

        invoice[tag] = partner_vals

    @api.model
    def _invoice_add_invoice_period(self, invoice, move, flow):
        invoice['InvoicePeriod'] = {
            'StartDate': {'_text': self._format_date(flow.period_start or move.date)},
            'EndDate': {'_text': self._format_date(flow.period_end or move.invoice_date_due or move.date)},
        }

    @api.model
    def _invoice_add_delivery_vals(self, invoice, move):
        if move.partner_shipping_id:
            location = {
                'LineOne': {'_text': move.partner_shipping_id.street},
                **({'LineTwo': {'_text': move.partner_shipping_id.street2}} if move.partner_shipping_id.street2 else {}),
                'CityName': {'_text': move.partner_shipping_id.city},
                'PostalZone': {'_text': move.partner_shipping_id.zip},
                **({'CountrySubentity': {'_text': move.partner_shipping_id.state_id}} if move.partner_shipping_id.state_id else {}),
                'CountryId': {'_text': drom_com_territories.map_country_code_for_ppf(move.partner_shipping_id.country_id.code)},
            }
            invoice['Delivery'] = {
                'Date': {'_text': self._format_date(move.date)},
                'Location': location,
            }

    @api.model
    def _invoice_add_seller_tax_representative(self, invoice, seller):
        '''Si la facture contient dans la ventilation de TVA le code "E" (Exonération) en TT-56,
        alors l'identifiant à la TVA du vendeur (TT-34) ou l'identifiant à la TVA du représentant
        fiscal du vendeur (TT-122) est obligatoire.
        Les entreprises en franchise en base ne disposant pas systématiquement d'un numéro de TVA
        pourront utiliser un code Z en TT-56.
        '''
        # if seller.vat:
        #     return
        # TODO: implement ? Seller always has TT-34, so this not usefull ??
        # invoice['SellerTaxRepresentative'] = {}
        pass

    @api.model
    def _invoice_add_allowance_charges(self, invoice, move, seller, buyer):
        # TODO: This is for disounts (ChargeIndicator = false). What about "Charges ou frais" see TG-21
        invoice['AllowanceCharge'] = []
        for line in move.invoice_line_ids:
            if not all((line.discount, line.price_unit, line.quantity)):
                continue
            base_amount = line.price_unit * line.quantity
            amount = float_round(abs(base_amount * (line.discount / 100.0)), 2)  # G1.14
            for tax in line.tax_ids or [False]:
                tax_code, _exemption_reason_code, _exemption_reason = self._get_tax_codes_and_exemption(buyer, seller, tax)
                invoice['AllowanceCharge'].append({
                    'Amount': {'_text': amount},
                    'TaxCategoryCode': {'_text': tax_code},
                    'TaxPercent': {'_text': tax.amount if tax else 0},
                    'ChargeIndicator': 'false',
                })

    @api.model
    def _invoice_add_monetary_total(self, invoice, move):
        invoice['MonetaryTotal'] = {
            'TaxExclusiveAmount': {'_text': move.amount_untaxed},  # invoice currency
            'TaxAmount': {
                '_text': float_round(abs(move.amount_tax_signed), 2),  # G1.14
                'CurrencyCode': 'EUR',
            },
        }

    @api.model
    def _get_tax_summary(self, move_lines, buyer=None, seller=None, line_validation_function=False, agregation_function=False):
        '''Returns tax summary for given move lines.
        If line_validation_function is given, only lines for which the function returns True
        are included in the summary.
        If agregation_function is given, summary is returned grouped by the value returned
        by the agregation function.
        '''
        summaries = defaultdict(lambda: {
            'taxable_amount_total': 0,
            'tax_total': 0,
            'subtotals': defaultdict(lambda: {
                'taxable_amount': 0,
                'tax_amount': 0,
                'tax_category_code': None,
                'exemption_reason': None,
                'exemption_code': None,
            }),
        })
        for line in move_lines:
            if (
                line.display_type != 'product'
                or (line_validation_function and not line_validation_function(line))
            ):
                continue

            summary = summaries[agregation_function(line) if agregation_function else None]

            if line.move_id.move_type == 'entry':
                price_unit = abs(line.amount_currency)
                quantity = 1.0
            else:
                price_unit = line.price_unit * (1 - line.discount / 100.0)
                quantity = line.quantity
            taxes_res = line.tax_ids.compute_all(
                price_unit=price_unit,
                currency=line.currency_id,
                quantity=quantity,
                product=line.product_id,
                partner=line.partner_id,
                is_refund=line.is_refund,
            )
            tax_items = taxes_res['taxes']
            for tax_item in tax_items:
                base_amount = line.currency_id.round(tax_item['base'])
                tax_amount = tax_item['amount']
                subtotal = summary['subtotals'][self.env['account.tax'].browse(tax_item['id'])]
                subtotal['taxable_amount'] += base_amount
                subtotal['tax_amount'] += tax_amount
                summary['taxable_amount_total'] += base_amount
                summary['tax_total'] += tax_amount
            if buyer and seller:
                for tax, values in summary['subtotals'].items():
                    tax_code, exemption_code, exemption_reason = self._get_tax_codes_and_exemption(buyer, seller, tax)
                    values['tax_category_code'] = tax_code
                    values['exemption_code'] = exemption_code
                    values['exemption_reason'] = exemption_reason

            if not tax_items:
                summary['subtotals'][None]['tax_category_code'] = 'E'

        return summaries if agregation_function else summaries[None]

    @api.model
    def _is_line_for_payment_reporting(self, line):
        return any(tax.tax_exigibility == 'on_payment' for tax in line.tax_ids)

    @api.model
    def _invoice_add_tax_sub_total(self, invoice, move, seller, buyer):
        invoice['TaxSubTotal'] = []
        tax_summary = self._get_tax_summary(move.line_ids, buyer, seller)
        for tax, tax_sub_total in tax_summary['subtotals'].items():
            invoice['TaxSubTotal'].append({
                'TaxableAmount': {'_text': float_round(tax_sub_total['taxable_amount'], 2)},  # G1.14
                'TaxAmount': {'_text': float_round(tax_sub_total['tax_amount'], 2)},  # G1.14
                'TaxCategory': {
                    'Code': {'_text': tax_sub_total['tax_category_code']},
                    'Percent': {'_text': tax.amount if tax else 0},
                    **({
                        'TaxExemptionReason': {'_text': tax_sub_total['exemption_reason']},
                        'TaxExemptionReasonCode': {'_text': tax_sub_total['exemption_code']},
                    } if tax_sub_total.get('exemption_code') else {}),
                }
            })

    @api.model
    def _invoice_add_lines(self, invoice, move):
        invoice['Line'] = []
        sale_line_ids_in_fields = 'sale_line_ids' in move.invoice_line_ids._fields
        for line in move.invoice_line_ids:
            if line.display_type != 'product':
                continue
            res = {
                'BilledQuantity': {
                    '_text': line.quantity,
                    'UnitCode': self._get_uom_unece_code(line.product_uom_id),
                },
            }
            if sale_line_ids_in_fields:
                refs = []
                for sale_line in line.sale_line_ids:
                    for previous_move in sale_line.invoice_lines.move_id:
                        if not previous_move or previous_move == move or previous_move.state != 'posted':
                            continue
                        refs.append((previous_move.name, previous_move.date))
                if refs:
                    ref_id, ref_date = sorted(refs, key=lambda vals: (vals[1] or fields.Date.today(), vals[0]))[0]
                    res['ReferencedDocument'] = {
                        'ID': {'_text': ref_id},
                        'IssueDate': {'_text': self._format_date(ref_date)},
                    }

            allowance_charge = float_round(line.price_unit * line.discount / 100.0, 6)  # G1.16
            allowance_charge_base = float_round(line.price_unit, 6)  # G1.16
            price = float_round(allowance_charge_base - allowance_charge, 6)  # G1.16
            res['Price'] = {
                'PriceAmount': {'_text': price},
                **(
                    {'AllowanceChargeAmount': {'_text': allowance_charge}}
                    if not float_is_zero(allowance_charge, 6)
                    else {}
                ),
                'AllowanceChargeBaseAmount': {'_text': allowance_charge_base},
            }
            res['Product'] = {
                'Name': {'_text': line.display_name},
            }

            invoice['Line'].append(res)

    @api.model
    def _get_tax_codes_and_exemption(self, buyer, seller, tax):
        tax_code = self._get_tax_category_code(buyer, seller, tax or self.env['account.tax'])
        if tax_code not in VALID_TAX_CODES:
            return 'S', None, None  # default to standard rate if tax code is not valid
        res = self._get_tax_exemption_reason(buyer, seller, tax or self.env['account.tax'])
        exemption_reason_code = res.get('tax_exemption_reason_code')
        exemption_reason = res.get('tax_exemption_reason')
        return tax_code, exemption_reason_code, exemption_reason

    @api.model
    def _get_move_business_process_id(self, move):
        """Determine billing framework code (TT-28) from invoice"""
        product_lines = move.invoice_line_ids.filtered(lambda ln: ln.display_type == 'product')
        scopes = set(product_lines.tax_ids.mapped('tax_scope'))
        if 'service' in scopes:
            if 'consu' in scopes:
                prefix = 'M'
            else:
                prefix = 'S'
        else:
            prefix = 'B'

        if move._is_downpayment():
            if any(line.display_type == 'product' and not line.is_downpayment for line in move.invoice_line_ids):
                suffix = '4'
            else:
                suffix = '2' if move.payment_state in ('paid', 'reversed') else '1'
        else:
            suffix = '1'
        return f'{prefix}{suffix}'

    @api.model
    def _get_move_typecode(self, move):
        if move.journal_id.is_self_billing:
            return '389' if move.is_inbound() else '261'
        else:
            return '380' if move.is_inbound() else '381'

    @api.model
    def _get_payments(self, flow):
        return {
            'PaymentsReport': {
                **self._get_report_period(flow),
            }
        }

    @api.model
    def _get_report_period(self, flow):
        return {
            'ReportPeriod': {
                'StartDate': self._format_date(flow.period_start),
                'EndDate': self._format_date(flow.period_end),
            }
        }

    @api.model
    def _format_date(self, date):
        """Format date as YYYYMMDD string."""
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        return date.strftime('%Y%m%d')

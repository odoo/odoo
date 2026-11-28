# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re
from collections import defaultdict

from lxml import etree
from stdnum.th import tin

from odoo import fields, models
from odoo.tools import float_repr

from odoo.addons.account.tools import dict_to_xml

ETDA_DOCUMENT_NAMES = {
    '388': 'ใบกำกับภาษี',
    'T03': 'ใบเสร็จรับเงิน/ใบกำกับภาษี',
    '80': 'ใบเพิ่มหนี้',
    '81': 'ใบลดหนี้',
}


class L10nThEdiDocument(models.AbstractModel):
    _name = 'l10n_th_edi.document'
    _description = "Thai e-Tax Document"

    l10n_th_edi_state = fields.Selection(
        selection=[
            ('ready_to_send', "Ready to send"),
            ('processing', "Processing"),
            ('error', "Error"),
            ('signed', "Signed"),
            ('unknown', "Unknown"),
        ],
        string="e-Tax Status",
        copy=False,
        readonly=True,
        help="Processing: the e-Tax provider received the document but has not signed it yet.\n"
             "Unknown: the provider's answer was lost. Odoo checks with the provider before sending it again.",
    )
    l10n_th_edi_rd_state = fields.Selection(
        selection=[
            ('waiting', "Waiting for RD"),
            ('sending', "Sending to RD"),
            ('in_review', "Under RD Review"),
            ('accepted', "Accepted by RD"),
            ('failed', "Failed at RD"),
        ],
        string="RD Status",
        copy=False,
        readonly=True,
        help="The e-Tax provider submits the signed documents to the Revenue Department (RD) by the RD's deadline.",
    )
    l10n_th_edi_error = fields.Text(string="e-Tax Error", copy=False, readonly=True)
    l10n_th_edi_xml_file_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Signed e-Tax XML",
        copy=False,
        readonly=True,
    )
    l10n_th_edi_pdf_file_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Signed e-Tax PDF",
        copy=False,
        readonly=True,
    )

    # -------------------------------------------------------------------------
    # HOOKS
    # -------------------------------------------------------------------------

    def _l10n_th_edi_get_document_values(self):
        """ Return the data of the e-Tax document as a dict with the keys:
            move, type_code, number, date, partner, currency, base_lines, tax_exigibility, ratio,
            and for credit and debit notes: references, purpose_code, purpose, original_amount, corrected_amount.
        """
        raise NotImplementedError()

    def _l10n_th_edi_get_pdf_content(self):
        raise NotImplementedError()

    def _l10n_th_edi_send(self):
        """ Have the e-Tax provider sign the document, and update it with the outcome. """
        raise NotImplementedError()

    # -------------------------------------------------------------------------
    # CHECKS
    # -------------------------------------------------------------------------

    def _l10n_th_edi_check(self, document_values):
        company = self.company_id
        partner = document_values['partner']
        errors = []
        if not tin.is_valid(company.vat or ''):
            errors.append(self.env._("The tax ID of %s must have 13 digits with a valid check digit.", company.display_name))
        if partner.country_code == 'TH' and partner.vat and not tin.is_valid(partner.vat):
            errors.append(self.env._("The tax ID of %s must have 13 digits with a valid check digit.", partner.display_name))
        if not (
            company.zip
            and company.partner_id._get_street_split()['street_number']
            and re.fullmatch(r'\d{6}', company.l10n_th_edi_subdistrict_code or '')
        ):
            errors.append(self.env._(
                "Set the street with its house number, the postcode and the 6-digit sub-district code of %s.",
                company.display_name,
            ))
        if not (partner.street and partner.zip and partner.country_id):
            errors.append(self.env._("Set the street, postcode and country of %s.", partner.display_name))
        if document_values['currency'].name != 'THB':
            errors.append(self.env._("e-Tax documents must be in Thai Baht."))
        return errors

    # -------------------------------------------------------------------------
    # XML
    # -------------------------------------------------------------------------

    def _l10n_th_edi_get_file_name(self, document_values):
        return f"{document_values['number'].replace('/', '_')}_etax"

    def _l10n_th_edi_format_datetime(self, date):
        return f'{date.isoformat()}T00:00:00'

    def _l10n_th_edi_get_tax_node(self, tax_key, base_amount, tax_amount, currency):
        type_code, rate = tax_key
        return {
            'ram:TypeCode': {'_text': type_code},
            'ram:CalculatedRate': {'_text': float_repr(rate, 2)},
            'ram:BasisAmount': {'_text': float_repr(base_amount, currency.decimal_places)},
            'ram:CalculatedAmount': {'_text': float_repr(tax_amount, currency.decimal_places)},
        }

    def _l10n_th_edi_get_seller_node(self):
        company = self.company_id
        subdistrict_code = company.l10n_th_edi_subdistrict_code
        return {
            'ram:Name': {'_text': company.name},
            'ram:SpecifiedTaxRegistration': {
                'ram:ID': {'_text': tin.compact(company.vat) + company._l10n_th_edi_get_branch_code(), 'schemeID': 'TXID'},
            },
            'ram:PostalTradeAddress': {
                'ram:PostcodeCode': {'_text': company.zip},
                'ram:LineOne': {'_text': company.street},
                'ram:LineTwo': {'_text': company.street2},
                'ram:CityName': {'_text': subdistrict_code[:4]},
                'ram:CitySubDivisionName': {'_text': subdistrict_code},
                'ram:CountryID': {'_text': company.country_code},
                'ram:CountrySubDivisionID': {'_text': subdistrict_code[:2]},
                'ram:BuildingNumber': {'_text': company.partner_id._get_street_split()['street_number']},
            },
        }

    def _l10n_th_edi_get_buyer_node(self, partner):
        if partner.country_code == 'TH' and partner.vat:
            vat = tin.compact(partner.vat)
            if partner.is_company:
                tax_id = {'_text': vat + (partner._get_additional_identifier('TH_BRANCH_CODE') or '00000'), 'schemeID': 'TXID'}
            else:
                tax_id = {'_text': vat, 'schemeID': 'NIDN'}
        else:
            tax_id = {'_text': 'N/A', 'schemeID': 'OTHR'}
        return {
            'ram:Name': {'_text': partner.name},
            'ram:SpecifiedTaxRegistration': {'ram:ID': tax_id},
            'ram:DefinedTradeContact': {
                'ram:EmailURIUniversalCommunication': {'ram:URIID': {'_text': partner.email}},
            },
            'ram:PostalTradeAddress': {
                'ram:PostcodeCode': {'_text': partner.zip},
                'ram:LineOne': {'_text': ", ".join(filter(None, (partner.street, partner.street2)))},
                'ram:LineTwo': {'_text': ", ".join(filter(None, (partner.city, partner.state_id.name)))},
                'ram:CountryID': {'_text': partner.country_code},
            },
        }

    def _l10n_th_edi_get_line_nodes(self, document_values):
        """ Return the line nodes, and the amounts per tax as {(type_code, rate): {'base': float, 'tax': float}}. """
        currency = document_values['currency']
        ratio = document_values['ratio']
        base_lines = document_values['base_lines']
        AccountTax = self.env['account.tax']
        AccountTax._add_and_round_raw_gross_total_excluded_and_discount(
            base_lines,
            self.company_id,
            precision_digits=currency.decimal_places,
        )
        exempt_tax_group = self.env['account.chart.template'].with_company(self.company_id).ref(
            'tax_group_exempt',
            raise_if_not_found=False,
        )
        quantity_digits = self.env['decimal.precision'].precision_get('Product Unit')

        def format_amount(amount):
            return float_repr(amount, currency.decimal_places)

        taxes_per_line = []
        raw_amount_per_tax = defaultdict(float)
        for base_line in base_lines:
            line_taxes = []
            for tax_data in base_line['tax_details']['taxes_data']:
                tax = tax_data['tax']
                if document_values['tax_exigibility'] and tax.tax_exigibility != document_values['tax_exigibility']:
                    continue
                raw_amount_per_tax[tax] += tax_data['tax_amount_currency'] * ratio
                line_taxes.append({
                    'tax': tax,
                    'base_amount': currency.round(tax_data['base_amount_currency'] * ratio),
                    'tax_amount': currency.round(tax_data['tax_amount_currency'] * ratio),
                })
            taxes_per_line.append(line_taxes)

        # As on the cash basis entry of a receipt, the paid share of each tax is rounded once, not per line.
        for tax, raw_amount in raw_amount_per_tax.items():
            tax_lines = [line_tax for line_taxes in taxes_per_line for line_tax in line_taxes if line_tax['tax'] == tax]
            deltas = AccountTax._distribute_delta_amount_smoothly(
                currency.decimal_places,
                currency.round(raw_amount) - sum(line_tax['tax_amount'] for line_tax in tax_lines),
                [{'factor': line_tax['tax_amount']} for line_tax in tax_lines],
            )
            for line_tax, delta in zip(tax_lines, deltas):
                line_tax['tax_amount'] += delta

        line_nodes = []
        amounts_per_tax = {}
        for line_number, (base_line, line_taxes) in enumerate(zip(base_lines, taxes_per_line), start=1):
            tax_details = base_line['tax_details']
            net_amount = currency.round(
                (tax_details['total_excluded_currency'] + tax_details['delta_total_excluded_currency']) * ratio,
            )
            line_tax_amount = 0.0
            tax_nodes = []
            for line_tax in line_taxes:
                tax = line_tax['tax']
                tax_key = ('FRE', 0.0) if tax.tax_group_id == exempt_tax_group else ('VAT', tax.amount)
                base_amount, tax_amount = line_tax['base_amount'], line_tax['tax_amount']
                amounts = amounts_per_tax.setdefault(tax_key, {'base': 0.0, 'tax': 0.0})
                amounts['base'] += base_amount
                amounts['tax'] += tax_amount
                line_tax_amount += tax_amount
                tax_nodes.append(self._l10n_th_edi_get_tax_node(tax_key, base_amount, tax_amount, currency))

            product = base_line['product_id']
            discount_amount = currency.round(tax_details['raw_discount_amount_currency'] * ratio)
            line_nodes.append({
                'ram:AssociatedDocumentLineDocument': {'ram:LineID': {'_text': line_number}},
                'ram:SpecifiedTradeProduct': {
                    'ram:ID': {'_text': product.default_code},
                    'ram:Name': {'_text': base_line['record'].label},
                },
                'ram:SpecifiedLineTradeAgreement': {
                    'ram:GrossPriceProductTradePrice': {
                        'ram:ChargeAmount': {'_text': format_amount(tax_details['raw_gross_price_unit_currency'] * ratio)},
                    },
                },
                'ram:SpecifiedLineTradeDelivery': {
                    'ram:BilledQuantity': {
                        '_text': float_repr(base_line['quantity'], quantity_digits),
                        # ETDA only expects a unit on goods.
                        'unitCode': product.type != 'service' and base_line['product_uom_id']._get_unece_code(),
                    },
                },
                'ram:SpecifiedLineTradeSettlement': {
                    'ram:ApplicableTradeTax': tax_nodes,
                    'ram:SpecifiedTradeAllowanceCharge': {
                        'ram:ChargeIndicator': {'_text': 'false'},
                        'ram:ActualAmount': {'_text': format_amount(discount_amount)},
                    } if discount_amount else None,
                    'ram:SpecifiedTradeSettlementLineMonetarySummation': {
                        'ram:TaxTotalAmount': {'_text': format_amount(line_tax_amount)},
                        'ram:NetLineTotalAmount': {'_text': format_amount(net_amount)},
                        'ram:NetIncludingTaxesLineTotalAmount': {'_text': format_amount(net_amount + line_tax_amount)},
                    },
                },
            })
        return line_nodes, amounts_per_tax

    def _l10n_th_edi_get_xml(self, document_values):
        type_code = document_values['type_code']
        currency = document_values['currency']
        root = 'DebitCreditNote' if type_code in ('80', '81') else 'TaxInvoice'
        nsmap = {
            'rsm': f'urn:etda:uncefact:data:standard:{root}_CrossIndustryInvoice:2',
            'ram': f'urn:etda:uncefact:data:standard:{root}_ReusableAggregateBusinessInformationEntity:2',
        }
        line_nodes, amounts_per_tax = self._l10n_th_edi_get_line_nodes(document_values)
        base_total = sum(amounts['base'] for amounts in amounts_per_tax.values())
        tax_total = sum(amounts['tax'] for amounts in amounts_per_tax.values())

        def format_amount(amount):
            return {'_text': float_repr(amount, currency.decimal_places)}

        if root == 'DebitCreditNote':
            # The VAT applies on the difference with the original document only.
            monetary_summation = {
                'ram:OriginalInformationAmount': format_amount(document_values['original_amount']),
                'ram:LineTotalAmount': format_amount(document_values['corrected_amount']),
                'ram:DifferenceInformationAmount': format_amount(base_total),
            }
        else:
            monetary_summation = {'ram:LineTotalAmount': format_amount(base_total)}
        monetary_summation.update({
            'ram:TaxBasisTotalAmount': format_amount(base_total),
            'ram:TaxTotalAmount': format_amount(tax_total),
            'ram:GrandTotalAmount': format_amount(base_total + tax_total),
        })

        document_node = {
            '_tag': f'rsm:{root}_CrossIndustryInvoice',
            'rsm:ExchangedDocumentContext': {
                'ram:GuidelineSpecifiedDocumentContextParameter': {
                    'ram:ID': {'_text': 'ER3-2560', 'schemeAgencyID': 'ETDA', 'schemeVersionID': 'v2.0'},
                },
            },
            'rsm:ExchangedDocument': {
                'ram:ID': {'_text': document_values['number']},
                'ram:Name': {'_text': ETDA_DOCUMENT_NAMES[type_code]},
                'ram:TypeCode': {'_text': type_code},
                'ram:IssueDateTime': {'_text': self._l10n_th_edi_format_datetime(document_values['date'])},
                'ram:Purpose': {'_text': document_values.get('purpose')},
                'ram:PurposeCode': {'_text': document_values.get('purpose_code')},
                'ram:CreationDateTime': {'_text': fields.Datetime.now().isoformat()},
            },
            'rsm:SupplyChainTradeTransaction': {
                'ram:ApplicableHeaderTradeAgreement': {
                    'ram:SellerTradeParty': self._l10n_th_edi_get_seller_node(),
                    'ram:BuyerTradeParty': self._l10n_th_edi_get_buyer_node(document_values['partner']),
                    'ram:AdditionalReferencedDocument': [
                        {
                            'ram:IssuerAssignedID': {'_text': reference['number']},
                            'ram:IssueDateTime': {'_text': self._l10n_th_edi_format_datetime(reference['date'])},
                            'ram:ReferenceTypeCode': {'_text': reference['type_code']},
                        }
                        for reference in document_values.get('references', [])
                    ],
                },
                'ram:ApplicableHeaderTradeDelivery': {'_empty': True},
                'ram:ApplicableHeaderTradeSettlement': {
                    'ram:InvoiceCurrencyCode': {'_text': currency.name},
                    'ram:ApplicableTradeTax': [
                        self._l10n_th_edi_get_tax_node(tax_key, amounts['base'], amounts['tax'], currency)
                        for tax_key, amounts in amounts_per_tax.items()
                    ],
                    'ram:SpecifiedTradeSettlementHeaderMonetarySummation': monetary_summation,
                },
                'ram:IncludedSupplyChainTradeLineItem': line_nodes,
            },
        }
        return etree.tostring(dict_to_xml(document_node, nsmap=nsmap), xml_declaration=True, encoding='UTF-8')

    def _l10n_th_edi_is_same_document(self, signed_xml, document_values):
        """ Whether a signed document found by this document's number is this document, and not another one issued with
        the same number. """
        paths = ('ExchangedDocument/TypeCode', 'BuyerTradeParty/SpecifiedTaxRegistration/ID', 'GrandTotalAmount')
        xpath = ' | '.join('//' + '/'.join(f"*[local-name()='{tag}']" for tag in path.split('/')) + '/text()' for path in paths)
        return etree.fromstring(signed_xml).xpath(xpath) == etree.fromstring(self._l10n_th_edi_get_xml(document_values)).xpath(xpath)

    # -------------------------------------------------------------------------
    # SENDING
    # -------------------------------------------------------------------------

    def action_l10n_th_edi_send(self):
        self.env['res.company']._with_locked_records(self)
        for document in self:
            document._l10n_th_edi_send()
            if self.env['account.move']._can_commit():
                self.env.cr.commit()

    def _l10n_th_edi_save_signed_files(self, xml_content, pdf_content, document_values):
        move = document_values['move']
        file_name = self._l10n_th_edi_get_file_name(document_values)
        xml_file, pdf_file = self.env['ir.attachment'].create([
            {
                'name': f'{file_name}.{extension}',
                'raw': content,
                'mimetype': mimetype,
                'res_model': move._name,
                'res_id': move.id,
            }
            for extension, content, mimetype in (
                ('xml', xml_content, 'application/xml'),
                ('pdf', pdf_content, 'application/pdf'),
            )
        ])
        self.write({'l10n_th_edi_xml_file_id': xml_file.id, 'l10n_th_edi_pdf_file_id': pdf_file.id})
        move.message_post(
            body=self.env._("e-Tax document %s signed.", document_values['number']),
            attachment_ids=(xml_file + pdf_file).ids,
        )

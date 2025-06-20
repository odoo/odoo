import base64
import re
from collections import defaultdict
from copy import deepcopy
from hashlib import sha1

from lxml import etree
from markupsafe import Markup

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_round, float_repr, date_utils, SQL
from odoo.tools.xml_utils import cleanup_xml_node, find_xml_value
from odoo.addons.l10n_es_edi_facturae.xml_utils import (
    NS_MAP,
    _canonicalize_node,
    _reference_digests,
)

PHONE_CLEAN_TABLE = str.maketrans({" ": None, "-": None, "(": None, ")": None, "+": None})
COUNTRY_CODE_MAP = {
    "BD": "BGD", "BE": "BEL", "BF": "BFA", "BG": "BGR", "BA": "BIH", "BB": "BRB", "WF": "WLF", "BL": "BLM", "BM": "BMU",
    "BN": "BRN", "BO": "BOL", "BH": "BHR", "BI": "BDI", "BJ": "BEN", "BT": "BTN", "JM": "JAM", "BV": "BVT", "BW": "BWA",
    "WS": "WSM", "BQ": "BES", "BR": "BRA", "BS": "BHS", "JE": "JEY", "BY": "BLR", "BZ": "BLZ", "RU": "RUS", "RW": "RWA",
    "RS": "SRB", "TL": "TLS", "RE": "REU", "TM": "TKM", "TJ": "TJK", "RO": "ROU", "TK": "TKL", "GW": "GNB", "GU": "GUM",
    "GT": "GTM", "GS": "SGS", "GR": "GRC", "GQ": "GNQ", "GP": "GLP", "JP": "JPN", "GY": "GUY", "GG": "GGY", "GF": "GUF",
    "GE": "GEO", "GD": "GRD", "GB": "GBR", "GA": "GAB", "SV": "SLV", "GN": "GIN", "GM": "GMB", "GL": "GRL", "GI": "GIB",
    "GH": "GHA", "OM": "OMN", "TN": "TUN", "JO": "JOR", "HR": "HRV", "HT": "HTI", "HU": "HUN", "HK": "HKG", "HN": "HND",
    "HM": "HMD", "VE": "VEN", "PR": "PRI", "PS": "PSE", "PW": "PLW", "PT": "PRT", "SJ": "SJM", "PY": "PRY", "IQ": "IRQ",
    "PA": "PAN", "PF": "PYF", "PG": "PNG", "PE": "PER", "PK": "PAK", "PH": "PHL", "PN": "PCN", "PL": "POL", "PM": "SPM",
    "ZM": "ZMB", "EH": "ESH", "EE": "EST", "EG": "EGY", "ZA": "ZAF", "EC": "ECU", "IT": "ITA", "VN": "VNM", "SB": "SLB",
    "ET": "ETH", "SO": "SOM", "ZW": "ZWE", "SA": "SAU", "ES": "ESP", "ER": "ERI", "ME": "MNE", "MD": "MDA", "MG": "MDG",
    "MF": "MAF", "MA": "MAR", "MC": "MCO", "UZ": "UZB", "MM": "MMR", "ML": "MLI", "MO": "MAC", "MN": "MNG", "MH": "MHL",
    "MK": "MKD", "MU": "MUS", "MT": "MLT", "MW": "MWI", "MV": "MDV", "MQ": "MTQ", "MP": "MNP", "MS": "MSR", "MR": "MRT",
    "IM": "IMN", "UG": "UGA", "TZ": "TZA", "MY": "MYS", "MX": "MEX", "IL": "ISR", "FR": "FRA", "IO": "IOT", "SH": "SHN",
    "FI": "FIN", "FJ": "FJI", "FK": "FLK", "FM": "FSM", "FO": "FRO", "NI": "NIC", "NL": "NLD", "NO": "NOR", "NA": "NAM",
    "VU": "VUT", "NC": "NCL", "NE": "NER", "NF": "NFK", "NG": "NGA", "NZ": "NZL", "NP": "NPL", "NR": "NRU", "NU": "NIU",
    "CK": "COK", "XK": "XKX", "CI": "CIV", "CH": "CHE", "CO": "COL", "CN": "CHN", "CM": "CMR", "CL": "CHL", "CC": "CCK",
    "CA": "CAN", "CG": "COG", "CF": "CAF", "CD": "COD", "CZ": "CZE", "CY": "CYP", "CX": "CXR", "CR": "CRI", "CW": "CUW",
    "CV": "CPV", "CU": "CUB", "SZ": "SWZ", "SY": "SYR", "SX": "SXM", "KG": "KGZ", "KE": "KEN", "SS": "SSD", "SR": "SUR",
    "KI": "KIR", "KH": "KHM", "KN": "KNA", "KM": "COM", "ST": "STP", "SK": "SVK", "KR": "KOR", "SI": "SVN", "KP": "PRK",
    "KW": "KWT", "SN": "SEN", "SM": "SMR", "SL": "SLE", "SC": "SYC", "KZ": "KAZ", "KY": "CYM", "SG": "SGP", "SE": "SWE",
    "SD": "SDN", "DO": "DOM", "DM": "DMA", "DJ": "DJI", "DK": "DNK", "VG": "VGB", "DE": "DEU", "YE": "YEM", "DZ": "DZA",
    "US": "USA", "UY": "URY", "YT": "MYT", "UM": "UMI", "LB": "LBN", "LC": "LCA", "LA": "LAO", "TV": "TUV", "TW": "TWN",
    "TT": "TTO", "TR": "TUR", "LK": "LKA", "LI": "LIE", "LV": "LVA", "TO": "TON", "LT": "LTU", "LU": "LUX", "LR": "LBR",
    "LS": "LSO", "TH": "THA", "TF": "ATF", "TG": "TGO", "TD": "TCD", "TC": "TCA", "LY": "LBY", "VA": "VAT", "VC": "VCT",
    "AE": "ARE", "AD": "AND", "AG": "ATG", "AF": "AFG", "AI": "AIA", "VI": "VIR", "IS": "ISL", "IR": "IRN", "AM": "ARM",
    "AL": "ALB", "AO": "AGO", "AQ": "ATA", "AS": "ASM", "AR": "ARG", "AU": "AUS", "AT": "AUT", "AW": "ABW", "IN": "IND",
    "AX": "ALA", "AZ": "AZE", "IE": "IRL", "ID": "IDN", "UA": "UKR", "QA": "QAT", "MZ": "MOZ"
}
REVERSED_COUNTRY_CODE = {v: k for k, v in COUNTRY_CODE_MAP.items()}

class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_es_edi_facturae_xml_id = fields.Many2one(
        comodel_name='ir.attachment',
        string="Facturae Attachment",
        compute=lambda self: self._compute_linked_attachment_id('l10n_es_edi_facturae_xml_id', 'l10n_es_edi_facturae_xml_file'),
        depends=['l10n_es_edi_facturae_xml_file']
    )
    l10n_es_edi_facturae_xml_file = fields.Binary(
        attachment=True,
        string="Facturae File",
        copy=False,
    )
    l10n_es_edi_facturae_reason_code = fields.Selection(
        selection=[
            ('01', "Invoice number"),
            ('02', "Invoice serial number"),
            ('03', "Issue date"),
            ('04', "Name and surnames/Corporate name - Issuer (Sender)"),
            ('05', "Name and surnames/Corporate name - Receiver"),
            ('06', "Issuer's Tax Identification Number"),
            ('07', "Receiver's Tax Identification Number"),
            ('08', "Issuer's address"),
            ('09', "Receiver's address"),
            ('10', "Item line"),
            ('11', "Applicable Tax Rate"),
            ('12', "Applicable Tax Amount"),
            ('13', "Applicable Date/Period"),
            ('14', "Invoice Class"),
            ('15', "Legal literals"),
            ('16', "Taxable Base"),
            ('80', "Calculation of tax outputs"),
            ('81', "Calculation of tax inputs"),
            ('82', "Taxable Base modified due to return of packages and packaging materials"),
            ('83', "Taxable Base modified due to discounts and rebates"),
            ('84', "Taxable Base modified due to firm court ruling or administrative decision"),
            ('85', "Taxable Base modified due to unpaid outputs where there is a judgement opening insolvency proceedings"),
        ], string='Spanish Facturae EDI Reason Code', default='10')
    l10n_es_invoicing_period_start_date = fields.Date(string="Invoice Period Start Date")
    l10n_es_invoicing_period_end_date = fields.Date(string="Invoice Period End Date")
    l10n_es_payment_means = fields.Selection(
        selection=[
            ('01', "In cash"),
            ('02', "Direct debit"),
            ('03', "Receipt"),
            ('04', "Credit transfer"),
            ('05', "Accepted bill of exchange"),
            ('06', "Documentary credit"),
            ('07', "Contract award"),
            ('08', "Bill of exchange"),
            ('09', "Transferable promissory note"),
            ('10', "Non transferable promissory note"),
            ('11', "Cheque"),
            ('12', "Open account reimbursement"),
            ('13', "Special payment"),
            ('14', "Set-off by reciprocal credits"),
            ('15', "Payment by postgiro"),
            ('16', "Certified cheque"),
            ('17', "Banker’s draft"),
            ('18', "Cash on delivery"),
            ('19', "Payment by card"),
        ], string="Payment Means", default='04')

    def _get_fields_to_detach(self):
        # EXTENDS account
        fields_list = super()._get_fields_to_detach()
        fields_list.append("l10n_es_edi_facturae_xml_file")
        return fields_list

    def _l10n_es_edi_facturae_get_default_enable(self):
        self.ensure_one()
        return not self.invoice_pdf_report_id \
            and not self.l10n_es_edi_facturae_xml_id \
            and not self.l10n_es_is_simplified \
            and self.is_invoice(include_receipts=True) \
            and (self.partner_id.is_company or self.partner_id.vat) \
            and self.company_id.country_code == 'ES' \
            and self.company_id.currency_id.name == 'EUR' \
            and self.company_id.sudo().l10n_es_edi_facturae_certificate_ids  # We only enable Facturae if a certificate is valid or has been valid (which will raise an error)

    def _l10n_es_edi_facturae_get_filename(self):
        self.ensure_one()
        return f'{self.name.replace("/", "_")}_facturae_signed.xml'

    def _l10n_es_edi_facturae_get_tax_period(self):
        self.ensure_one()
        if self.env['res.company'].fields_get(['account_tax_periodicity']):
            period_start, period_end = self.company_id._get_tax_closing_period_boundaries(self.date, self.env.ref('l10n_es.mod_303'))
        else:
            period_start = date_utils.start_of(self.date, 'month')
            period_end = date_utils.end_of(self.date, 'month')

        return {'start':period_start, 'end':period_end}

    def _l10n_es_edi_facturae_get_refunded_invoices(self):
        self.env['account.partial.reconcile'].flush_model()
        invoices_refunded_mapping = {invoice.id: invoice.reversed_entry_id.id for invoice in self}

        stored_ids = tuple(self.ids)
        queries = []
        for source_field, counterpart_field in (
            ('debit_move_id', 'credit_move_id'),
            ('credit_move_id', 'debit_move_id'),
        ):
            queries.append(SQL('''
                SELECT
                    source_line.move_id AS source_move_id,
                    counterpart_line.move_id AS counterpart_move_id
                FROM account_partial_reconcile part
                JOIN account_move_line source_line ON source_line.id = part.%s
                JOIN account_move_line counterpart_line ON counterpart_line.id = part.%s
                WHERE source_line.move_id IN %s AND counterpart_line.move_id != source_line.move_id
                GROUP BY source_move_id, counterpart_move_id
            ''', SQL.identifier(source_field), SQL.identifier(counterpart_field), stored_ids))
        payment_data = defaultdict(list)
        for row in self.env.execute_query_dict(SQL(" UNION ALL ").join(queries)):
            payment_data[row['source_move_id']].append(row)

        for invoice in self:
            if not invoice.move_type.endswith('refund'):
                # We only want to map refunds
                continue

            for move_id in (record_dict['counterpart_move_id'] for record_dict in payment_data.get(invoice.id, [])):
                invoices_refunded_mapping[invoice.id] = move_id
        return invoices_refunded_mapping

    def _l10n_es_edi_facturae_get_corrective_data(self):
        self.ensure_one()
        if self.move_type.endswith('refund'):
            if not self.reversed_entry_id:
                raise UserError(_("The credit note/refund appears to have been issued manually. For the purpose of "
                                  "generating a Facturae document, it's necessary that the credit note/refund is created "
                                  "directly from the associated invoice/bill."))

            refunded_invoice = self.env['account.move'].browse(self._l10n_es_edi_facturae_get_refunded_invoices()[self.id])
            tax_period = refunded_invoice._l10n_es_edi_facturae_get_tax_period()

            reason_code = self.l10n_es_edi_facturae_reason_code or '10'
            reason_description = [label for code, label in self._fields['l10n_es_edi_facturae_reason_code'].selection
                                  if code == reason_code][0]
            return {
                'refunded_invoice_record': refunded_invoice,
                'ReasonCode': reason_code,
                'Reason': reason_description,
                'TaxPeriod': {
                    'StartDate': tax_period.get('start'),
                    'EndDate': tax_period.get('end'),
                }
            }
        return {}

    def _l10n_es_edi_facturae_get_administrative_centers(self, partner):
        self.ensure_one()
        administrative_centers = []
        for ac in partner.child_ids.filtered(lambda p: p.type == 'facturae_ac'):
            ac_template = {
                'center_code': ac.l10n_es_edi_facturae_ac_center_code,
                'name': ac.name,
                'partner': ac,
                'partner_country_code': COUNTRY_CODE_MAP[ac.country_code],
                'partner_phone': ac.phone.translate(PHONE_CLEAN_TABLE) if ac.phone else False,
                'physical_gln': ac.l10n_es_edi_facturae_ac_physical_gln,
                'logical_operational_point': ac.l10n_es_edi_facturae_ac_logical_operational_point,
            }
            # An administrative center can have multiple roles, each of which should be reported separately.
            for role in ac.l10n_es_edi_facturae_ac_role_type_ids or [self.env['l10n_es_edi_facturae.ac_role_type']]:
                administrative_centers.append({
                    **ac_template,
                    'role_type_code': role.code,
                })
        return administrative_centers

    def _l10n_es_edi_facturae_get_tax_node_from_tax_data(self, values):
        self.ensure_one()
        tax = values['grouping_key']
        return {
            'tax_record': tax,
            'TaxRate': f'{abs(tax.amount):.3f}',
            'TaxableBase': {
                'TotalAmount': self.currency_id.round(values['raw_base_amount_currency']),
                'EquivalentInEuros': self.company_currency_id.round(values['raw_base_amount']),
            },
            'TaxAmount': {
                'TotalAmount': self.currency_id.round(abs(values['raw_tax_amount_currency'])),
                'EquivalentInEuros': self.company_currency_id.round(abs(values['raw_tax_amount'])),
            },
        }

    def _l10n_es_edi_facturae_convert_payment_terms_to_installments(self):
        """
        Convert the payments terms to a list of <Installment> elements to be used in the
        <PaymentDetails> node of the Facturae XML generation.
        """
        self.ensure_one()
        installments = []
        if self.is_inbound() and self.partner_bank_id:
            for payment_term in self.line_ids.filtered(lambda l: l.display_type == 'payment_term').sorted('date_maturity'):
                installments.append({
                    'InstallmentDueDate': payment_term.date_maturity,
                    'InstallmentAmount': payment_term.amount_residual_currency,
                    'PaymentMeans': self.l10n_es_payment_means,
                    'AccountToBeCredited': {
                        'IBAN': self.partner_bank_id.sanitized_acc_number,
                        'BIC': self.partner_bank_id.bank_bic,
                    },
                })
        return installments

    def _l10n_es_edi_facturae_prepare_inv_line(self, base_line, aggregated_values):
        """
        Convert the invoice lines to a list of items required for the Facturae xml generation

        :return: A tuple containing the Face items, the taxes and the invoice totals data.
        """
        self.ensure_one()
        extended_dp = 6 if self.company_id.tax_calculation_rounding_method == 'round_globally' else 2
        invoice_ref = self.ref and self.ref[:20]
        line = base_line['record']
        tax_details = base_line['tax_details']

        receiver_transaction_reference = (
            line.sale_line_ids.order_id.client_order_ref[:20]
            if 'sale_line_ids' in line._fields and line.sale_line_ids.order_id.client_order_ref
            else invoice_ref
        )

        xml_values = {
            'ReceiverTransactionReference': receiver_transaction_reference,
            'FileReference': invoice_ref,
            'ReceiverContractReference': invoice_ref,
            'FileDate': fields.Date.context_today(self),
            'ItemDescription': line.name,
            'Quantity': line.quantity,
            'UnitOfMeasure': line.product_uom_id.l10n_es_edi_facturae_uom_code,
            'DiscountsAndRebates': [],
            'Charges': [],
            'GrossAmount': line.price_subtotal,
        }

        if line.discount == 100.0:
            raw_total_cost = line.price_unit * line.quantity
        else:
            raw_total_cost = tax_details['total_excluded_currency'] / (1 - (line.discount / 100.0))
        xml_values['TotalCost'] = line.currency_id.round(raw_total_cost)

        if line.quantity:
            xml_values['UnitPriceWithoutTax'] = float_round(raw_total_cost / line.quantity, precision_digits=extended_dp)
        else:
            xml_values['UnitPriceWithoutTax'] = 0.0

        raw_discount_amount = xml_values['TotalCost'] - line.price_subtotal
        discount_amount = max(raw_discount_amount, 0.0)
        if discount_amount:
            xml_values['DiscountsAndRebates'].append({
                'DiscountReason': '/',
                'DiscountRate': f'{line.discount:.2f}',
                'DiscountAmount': discount_amount,
            })

        surcharge_amount = -min(0.0, raw_discount_amount)
        if surcharge_amount:
            xml_values['Charges'].append({
                'ChargeReason': '/',
                'ChargeRate': f'{-line.discount:.2f}',
                'ChargeAmount': surcharge_amount,
            })

        xml_values['TaxesOutputs'] = [
            self._l10n_es_edi_facturae_get_tax_node_from_tax_data(values)
            for values in aggregated_values.values()
            if values['grouping_key'] and values['grouping_key'].amount >= 0.0
        ]
        xml_values['TaxesWithheld'] = [
            self._l10n_es_edi_facturae_get_tax_node_from_tax_data(values)
            for values in aggregated_values.values()
            if values['grouping_key'] and values['grouping_key'].amount < 0.0
        ]

        return xml_values

    def _l10n_es_edi_facturae_export_facturae(self):
        """
        Produce the Facturae XML data for the invoice.

        :return: (data needed to render the full template, data needed to render the signature template)
        """
        def extract_party_name(party):
            name = {'firstname': 'UNKNOWN', 'surname': 'UNKNOWN', 'surname2': ''}
            if not party.is_company:
                name_split = [part for part in party.name.replace(', ', ' ').split(' ') if part]
                if len(name_split) > 2:
                    name['firstname'] = ' '.join(name_split[:-2])
                    name['surname'], name['surname2'] = name_split[-2:]
                elif len(name_split) == 2:
                    name['firstname'] = ' '.join(name_split[:-1])
                    name['surname'] = name_split[-1]
            return name

        self.ensure_one()
        company = self.company_id
        partner = self.commercial_partner_id

        if not company.vat:
            raise UserError(_('The company needs a set tax identification number or VAT number'))
        if not partner.vat:
            raise UserError(_('The partner needs a set tax identification number or VAT number'))
        if not partner.country_id:
            raise UserError(_("The partner needs a set country"))
        if self.move_type == "entry":
            return False

        operation_date = None
        if self.delivery_date and self.delivery_date != self.invoice_date:
            operation_date = self.delivery_date.isoformat()

        # Multi-currencies.
        eur_curr = self.env['res.currency'].search([('name', '=', 'EUR')])
        inv_curr = self.currency_id
        conversion_needed = inv_curr != eur_curr

        # Invoice xml values.
        invoice_ref = self.ref and self.ref[:20]
        legal_literals = self.narration and self.narration.striptags()
        legal_literals = legal_literals.split(";") if legal_literals else False
        invoice_values = {
            'invoice_record': self,
            'invoice_currency': inv_curr,
            'InvoiceDocumentType': 'FA' if self.l10n_es_is_simplified else 'FC',
            'InvoiceClass': 'OR' if self.move_type in ['out_refund', 'in_refund'] else 'OO',
            'Corrective': self._l10n_es_edi_facturae_get_corrective_data(),
            'InvoiceIssueData': {
                'OperationDate': operation_date,
                'ExchangeRateDetails': conversion_needed,
                'ExchangeRate': f"{round(self.invoice_currency_rate, 4):.4f}",
                'LanguageName': self._context.get('lang', 'en_US').split('_')[0],
                'InvoicingPeriod': None,
                'ReceiverTransactionReference': invoice_ref,
                'FileReference': invoice_ref,
                'ReceiverContractReference': invoice_ref,
            },
            'TaxOutputs': [],
            'TaxesWithheld': [],
            'TotalGrossAmount': 0.0,
            'TotalGeneralDiscounts': 0.0,
            'TotalGeneralSurcharges': 0.0,
            'TotalGrossAmountBeforeTaxes': 0.0,
            'TotalTaxOutputs': 0.0,
            'TotalTaxesWithheld': 0.0,
            'PaymentsOnAccount': [],
            'TotalOutstandingAmount': abs(self.amount_total_in_currency_signed),
            'InvoiceTotal': abs(self.amount_total_in_currency_signed),
            'TotalPaymentsOnAccount': 0.0,
            'AmountsWithheld': None,
            'TotalExecutableAmount': abs(self.amount_total_in_currency_signed),
            'Items': [],
            'PaymentDetails': self._l10n_es_edi_facturae_convert_payment_terms_to_installments(),
            'LegalLiterals': legal_literals,
        }

        # Taxes.
        AccountTax = self.env['account.tax']
        base_amls = self.invoice_line_ids.filtered(lambda line: line.display_type == 'product')
        base_lines = [self._prepare_product_base_line_for_taxes_computation(line) for line in base_amls]
        AccountTax._add_tax_details_in_base_lines(base_lines, self.company_id)
        tax_amls = self.line_ids.filtered('tax_repartition_line_id')
        tax_lines = [self._prepare_tax_line_for_taxes_computation(tax_line) for tax_line in tax_amls]
        AccountTax._round_base_lines_tax_details(base_lines, self.company_id, tax_lines=tax_lines)

        def grouping_function(base_line, tax_data):
            return tax_data['tax'] if tax_data else None

        base_lines_aggregated_values = AccountTax._aggregate_base_lines_tax_details(base_lines, grouping_function)
        for base_line, aggregated_values in base_lines_aggregated_values:
            invoice_line_values = self._l10n_es_edi_facturae_prepare_inv_line(base_line, aggregated_values)
            invoice_values['TotalGrossAmount'] += invoice_line_values['GrossAmount']
            invoice_values['Items'].append(invoice_line_values)

            for values in aggregated_values.values():
                tax = values['grouping_key']
                if not tax:
                    continue

                tax_data = self._l10n_es_edi_facturae_get_tax_node_from_tax_data(values)
                if tax.amount < 0.0:
                    invoice_values['TaxesWithheld'].append(tax_data)
                    invoice_values['TotalTaxesWithheld'] += tax_data['TaxAmount']['TotalAmount']
                else:
                    invoice_values['TaxOutputs'].append(tax_data)
                    invoice_values['TotalTaxOutputs'] += tax_data['TaxAmount']['TotalAmount']

        invoice_values['TotalGrossAmountBeforeTaxes'] = (
            invoice_values['TotalGrossAmount']
            - invoice_values['TotalGeneralDiscounts']
            + invoice_values['TotalGeneralSurcharges']
        )

        template_values = {
            'self_party': company.partner_id,
            'self_party_country_code': COUNTRY_CODE_MAP[company.country_id.code],
            'self_party_name': extract_party_name(company.partner_id),
            'self_party_administrative_centers': self._l10n_es_edi_facturae_get_administrative_centers(company.partner_id),
            'other_party': partner,
            'other_party_country_code': COUNTRY_CODE_MAP[partner.country_id.code],
            'other_party_phone': partner.phone.translate(PHONE_CLEAN_TABLE) if partner.phone else False,
            'other_party_name': extract_party_name(partner),
            'other_party_administrative_centers': self._l10n_es_edi_facturae_get_administrative_centers(partner),
            'is_outstanding': self.move_type.startswith('out_'),
            'float_repr': float_repr,
            'file_currency': inv_curr,
            'eur': eur_curr,
            'conversion_needed': conversion_needed,
            'refund_multiplier': -1 if self.move_type in ('out_refund', 'in_refund') else 1,

            'Modality': 'I',
            'BatchIdentifier': self.name,
            'InvoicesCount': 1,
            'TotalInvoicesAmount': {
                'TotalAmount': abs(self.amount_total_in_currency_signed),
                'EquivalentInEuros': abs(self.amount_total_signed),
            },
            'TotalOutstandingAmount': {
                'TotalAmount': abs(self.amount_total_in_currency_signed),
                'EquivalentInEuros': abs(self.amount_total_signed),
            },
            'TotalExecutableAmount': {
                'TotalAmount': abs(self.amount_total_in_currency_signed),
                'EquivalentInEuros': abs(self.amount_total_signed),
            },
            'InvoiceCurrencyCode': inv_curr.name,
            'Invoices': [invoice_values],
        }
        if self.l10n_es_invoicing_period_start_date and self.l10n_es_invoicing_period_end_date:
            template_values['Invoices'][0]['InvoiceIssueData']['InvoicingPeriod'] = {
                'StartDate': self.l10n_es_invoicing_period_start_date,
                'EndDate': self.l10n_es_invoicing_period_end_date,
            }

        invoice_issuer_signature_type = 'supplier' if self.move_type == 'out_invoice' else 'customer'
        signature_values = {'SigningTime': '', 'SignerRole': invoice_issuer_signature_type}
        return template_values, signature_values

    def _l10n_es_edi_facturae_render_facturae(self):
        """
        Produce the Facturae XML file for the invoice.

        :return: rendered xml file string.
        :rtype:  str
        """
        self.ensure_one()
        company = self.company_id
        template_values, signature_values = self._l10n_es_edi_facturae_export_facturae()
        xml_content = cleanup_xml_node(self.env['ir.qweb']._render('l10n_es_edi_facturae.account_invoice_facturae_export', template_values))

        errors = []
        try:
            xml_content = self._l10n_es_facturae_sign_xml(xml_content, signature_values)
        except ValueError:
            errors.append(_('No valid certificate found for this company, Facturae EDI file will not be signed.\n'))
        return xml_content, errors

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _get_edi_decoder(self, file_data, new=False):
        def is_facturae(tree):
            return tree.tag in [
                '{http://www.facturae.es/Facturae/2014/v3.2.1/Facturae}Facturae',
                '{http://www.facturae.gob.es/formato/Versiones/Facturaev3_2_2.xml}Facturae',
            ]

        if file_data['type'] == 'xml' and is_facturae(file_data['xml_tree']):
            return self._import_invoice_facturae

        return super()._get_edi_decoder(file_data, new=new)

    def _import_invoice_facturae(self, invoice, file_data, new=False):
        tree = file_data['xml_tree']
        is_bill = invoice.move_type.startswith('in_')
        partner = self._import_get_partner(tree, is_bill)
        self._import_invoice_facturae_invoices(invoice, partner, tree)

    def _import_get_partner(self, tree, is_bill):
        # If we're dealing with a vendor bill, then the partner is the seller party, if an invoice then it's the buyer.
        party = tree.xpath('//SellerParty') if is_bill else tree.xpath('//BuyerParty')
        if party:
            partner_vals = self._import_extract_partner_values(party[0])
            return self._import_create_or_retrieve_partner(partner_vals)
        return None

    def _import_extract_partner_values(self, party_node):
        name = find_xml_value('.//CorporateName|.//Name', party_node)
        first_surname = find_xml_value('.//FirstSurname', party_node)
        second_surname = find_xml_value('.//SecondSurname', party_node)
        phone = find_xml_value('.//Telephone', party_node)
        mail = find_xml_value('.//ElectronicMail', party_node)
        country_code = find_xml_value('.//CountryCode', party_node)
        vat = find_xml_value('.//TaxIdentificationNumber', party_node)

        full_name = ' '.join(part for part in [name, first_surname, second_surname] if part)

        return {'name': full_name, 'vat': vat, 'phone': phone, 'email': mail, 'country_code': country_code}

    def _import_create_or_retrieve_partner(self, partner_vals):
        name = partner_vals['name']
        vat = partner_vals['vat']
        phone = partner_vals['phone']
        email = partner_vals['email']
        country_code = partner_vals['country_code']

        partner = self.env['res.partner']._retrieve_partner(name=name, vat=vat, phone=phone, email=email)

        if not partner and name:
            partner_vals = {'name': name, 'email': email, 'phone': phone}
            country_code = REVERSED_COUNTRY_CODE.get(country_code)
            country = self.env['res.country'].search([('code', '=', country_code)]) if country_code else False
            if country:
                partner_vals['country_id'] = country.id
            partner = self.env['res.partner'].create(partner_vals)
            if vat and self.env['res.partner']._run_vat_test(vat, country):
                partner.vat = vat

        return partner

    def _import_invoice_facturae_invoices(self, invoice, partner, tree):
        invoices = tree.xpath('//Invoice')
        if not invoices:
            return

        self._import_invoice_facturae_invoice(invoice, partner, invoices[0])

        # There might be other invoices inside the facturae.
        for node in invoices[1:]:
            other_invoice = invoice.create({
                'journal_id': invoice.journal_id.id,
                'move_type': invoice.move_type
            })
            with other_invoice._get_edi_creation():
                self._import_invoice_facturae_invoice(other_invoice, partner, node)
                other_invoice.message_post(body=_("Created from attachment in %s", invoice._get_html_link()))

    def _import_invoice_facturae_invoice(self, invoice, partner, tree):
        logs = []

        # ==== move_type ====
        invoice_total = find_xml_value('.//InvoiceTotal', tree)
        is_refund = float(invoice_total) < 0 if invoice_total else False
        if is_refund:
            invoice.move_type = "in_refund" if invoice.move_type.startswith("in_") else "out_refund"
        ref_multiplier = -1.0 if is_refund else 1.0

        # ==== partner_id ====
        if partner:
            invoice.partner_id = partner
        else:
            logs.append(_("Customer/Vendor could not be found and could not be created due to missing data in the XML."))

        # ==== currency_id ====
        invoice_currency_code = find_xml_value('.//InvoiceCurrencyCode', tree)
        if invoice_currency_code:
            currency = self.env['res.currency'].search([('name', '=', invoice_currency_code)], limit=1)
            if currency:
                invoice.currency_id = currency
            else:
                logs.append(_("Could not retrieve currency: %s. Did you enable the multicurrency option "
                              "and activate the currency?", invoice_currency_code))

        # ==== invoice date ====
        if issue_date := find_xml_value('.//IssueDate', tree):
            invoice.invoice_date = issue_date

        # ==== invoice_date_due ====
        if end_date := find_xml_value('.//InstallmentDueDate', tree):
            invoice.invoice_date_due = end_date

        # ==== ref ====
        if invoice_number := find_xml_value('.//InvoiceNumber', tree):
            invoice.ref = invoice_number

        # ==== narration ====
        invoice.narration = "\n".join(
            ref.text
            for ref in tree.xpath('.//LegalReference')
            if ref.text
        )

        # === invoice_line_ids ===
        logs += self._import_invoice_fill_lines(invoice, tree, ref_multiplier)

        body = Markup("<strong>%s</strong>") % _("Invoice imported from Factura-E XML file.")

        if logs:
            body += Markup("<ul>%s</ul>") \
                    % Markup().join(Markup("<li>%s</li>") % log for log in logs)

        invoice.message_post(body=body)

        return logs

    def _import_invoice_fill_lines(self, invoice, tree, ref_multiplier):
        lines = tree.xpath('.//InvoiceLine')
        logs = []
        vals_list = []
        for line in lines:
            line_vals = {'move_id': invoice.id}

            # ==== name ====
            if item_description := find_xml_value('.//ItemDescription', line):
                product = self._search_product_for_import(item_description)
                if product:
                    line_vals['product_id'] = product.id
                else:
                    logs.append(_("The product '%s' could not be found.", item_description))
                line_vals['name'] = item_description

            # ==== quantity ====
            line_vals['quantity'] = find_xml_value('.//Quantity', line) or 1

            # ==== price_unit ====
            price_unit = find_xml_value('.//UnitPriceWithoutTax', line)
            line_vals['price_unit'] = ref_multiplier * float(price_unit) if price_unit else 1.0

            # ==== discount ====
            discounts = line.xpath('.//DiscountRate')
            discount_rate = 0.0
            for discount in discounts:
                discount_rate += float(discount.text)

            charges = line.xpath('.//ChargeRate')
            charge_rate = 0.0
            for charge in charges:
                charge_rate += float(charge.text)

            discount_rate -= charge_rate
            line_vals['discount'] = discount_rate

            # ==== tax_ids ====
            taxes_withheld_nodes = line.xpath('.//TaxesWithheld/Tax')
            taxes_outputs_nodes = line.xpath('.//TaxesOutputs/Tax')
            is_purchase = invoice.move_type.startswith('in')
            tax_ids = []
            logs += self._import_fill_invoice_line_taxes(invoice, line_vals, tax_ids, taxes_outputs_nodes, False, is_purchase)
            logs += self._import_fill_invoice_line_taxes(invoice, line_vals, tax_ids, taxes_withheld_nodes, True, is_purchase)
            line_vals['tax_ids'] = [Command.set(tax_ids)]
            vals_list.append(line_vals)

        invoice.invoice_line_ids = self.env['account.move.line'].create(vals_list)
        return logs

    def _import_fill_invoice_line_taxes(self, invoice, line_vals, tax_ids, tax_nodes, is_withheld, is_purchase):
        logs = []
        for tax_node in tax_nodes:
            tax_rate = find_xml_value('.//TaxRate', tax_node)
            if tax_rate:
                # Since the 'TaxRate' node isn't guaranteed to be a percentage, we can find out by
                # applying the tax rate on the taxable base, and if it's equal to the tax amount
                # then we can say this is a percentage, otherwise a fixed amount.
                taxable_base = find_xml_value('.//TaxableBase/TotalAmount', tax_node)
                tax_amount = find_xml_value('.//TaxAmount/TotalAmount', tax_node)
                is_fixed = False

                if taxable_base and tax_amount and invoice.currency_id.compare_amounts(float(taxable_base) * (float(tax_rate) / 100), float(tax_amount)) != 0:
                    is_fixed = True

                tax_excl = self._search_tax_for_import(invoice.company_id, float(tax_rate), is_fixed, is_withheld, is_purchase, price_included=False)

                if tax_excl:
                    tax_ids.append(tax_excl.id)
                elif tax_incl := self._search_tax_for_import(invoice.company_id, float(tax_rate), is_fixed, is_withheld, is_purchase, price_included=True):
                    tax_ids.append(tax_incl)
                    line_vals['price_unit'] *= (1.0 + float(tax_rate) / 100.0)
                else:
                    logs.append(_("Could not retrieve the tax: %(tax_rate)s %% for line '%(line)s'.", tax_rate=tax_rate, line=line_vals.get('name', "")))

        return logs

    def _search_tax_for_import(self, company, amount, is_fixed, is_withheld, is_purchase, price_included):
        taxes = self.env['account.tax'].search([
            ('company_id', '=', company.id),
            ('amount', '=', -1.0 * amount if is_withheld else amount),
            ('amount_type', '=', 'fixed' if is_fixed else 'percent'),
            ('type_tax_use', '=', 'purchase' if is_purchase else 'sale'),
            ('price_include', '=', price_included),
        ], limit=1)

        return taxes

    def _search_product_for_import(self, item_description):
        # Exported Odoo XML will have item_description = "[default_code] name".
        # We can check if it follows the same format and search for the product with the default code and the name.
        code_and_name = re.match(r"(\[(?P<default_code>.*?)\]\s)?(?P<name>.*)", item_description).groupdict()
        product = self.env['product.product']._retrieve_product(**code_and_name)
        return product

    # -------------------------------------------------------------------------
    # BUSINESS METHODS                                                        #
    # -------------------------------------------------------------------------
    def _l10n_es_facturae_sign_xml(self, edi_data, signature_data):
        """
        Signs the given XML data with the certificate and private key.

        :param etree._Element edi_data: The XML data to sign.
        :param dict signature_data: The signature data to use.
        :return: The signed XML data string.
        :rtype: str
        """
        self.ensure_one()
        certificates_sudo = self.company_id.sudo().l10n_es_edi_facturae_certificate_ids.filtered("is_valid")
        if not certificates_sudo:
            raise UserError(_('No valid certificate found'))

        certificate_sudo = certificates_sudo[0]

        root = deepcopy(edi_data)
        e, n = certificate_sudo._get_public_key_numbers_bytes()
        issuer = certificate_sudo._l10n_es_edi_facturae_get_issuer()

        # Identifiers
        document_id = f"Document-{sha1(etree.tostring(edi_data)).hexdigest()}"
        signature_id = f"Signature-{document_id}"
        keyinfo_id = f"KeyInfo-{document_id}"
        sigproperties_id = f"SignatureProperties-{document_id}"

        signature_data.update({
            'document_id': document_id,
            'x509_certificate': base64.encodebytes(base64.b64decode(certificate_sudo._get_der_certificate_bytes())).decode(),
            'public_modulus': n.decode(),
            'public_exponent': e.decode(),
            'iso_now': fields.datetime.now().isoformat(),
            'keyinfo_id': keyinfo_id,
            'signature_id': signature_id,
            'sigproperties_id': sigproperties_id,
            'reference_uri': f"Reference-{document_id}",
            'sigpolicy_url': "http://www.facturae.es/politica_de_firma_formato_facturae/politica_de_firma_formato_facturae_v3_1.pdf",
            'sigpolicy_description': "Política de firma electrónica para facturación electrónica con formato Facturae",
            'sigcertif_digest': certificate_sudo._get_fingerprint_bytes(formatting='base64').decode(),
            'x509_issuer_description': issuer,
            'x509_serial_number': int(certificate_sudo.serial_number),
        })
        signature = self.env['ir.qweb']._render('l10n_es_edi_facturae.template_xades_signature', signature_data)
        signature = cleanup_xml_node(signature, remove_blank_nodes=False)
        root.append(signature)
        _reference_digests(signature.find("ds:SignedInfo", namespaces=NS_MAP))

        signed_info_xml = signature.find("ds:SignedInfo", namespaces=NS_MAP)
        signature.find("ds:SignatureValue", namespaces=NS_MAP).text = certificate_sudo._sign(_canonicalize_node(signed_info_xml)).decode()

        return etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True)

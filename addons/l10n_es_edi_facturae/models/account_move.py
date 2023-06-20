from collections import defaultdict

from odoo import fields, models, api, _
from odoo.exceptions import UserError
from odoo.tools import float_repr, date_utils
from odoo.tools.xml_utils import cleanup_xml_node

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
            ('01', 'Invoice number'),
            ('02', 'Invoice series'),
            ('03', 'Date of issue'),
            ('04', 'Name and surname/company name - Issuer'),
            ('05', 'Name and surname/company name - Recipient'),
            ('06', 'Tax identification Issuer/Oblige'),
            ('07', 'Tax identification Receiver'),
            ('08', 'Issuer/Oblige Address'),
            ('09', 'Receiving Address'),
            ('10', 'Transaction Details'),
            ('11', 'Tax rate to be applied'),
            ('12', 'Tax rate to be applied'),
            ('13', 'Date/Period to apply'),
            ('14', 'Invoice type'),
            ('15', 'Statutory letters'),
            ('16', 'Taxable amount'),
            ('80', 'Calculation of output quotas'),
            ('81', 'Calculation of withholding taxes'),
            ('82', 'Taxable amount modified by return of containers/packaging'),
            ('83', 'Taxable income modified by discounts and allowances'),
            ('84', 'Taxable income modified by final, judicial or administrative ruling'),
            ('85', 'Taxable income modified by unpaid tax assessments. Order of declaration of bankruptcy'),
        ], string='Spanish Facturae EDI Reason Code', default='10')

    def _l10n_es_edi_facturae_get_default_enable(self):
        self.ensure_one()
        return not self.invoice_pdf_report_id \
            and not self.l10n_es_edi_facturae_xml_id \
            and self.is_invoice(include_receipts=True) \
            and self.company_id.country_code == 'ES' \
            and self.company_id.currency_id.name == 'EUR'

    def _l10n_es_edi_facturae_get_filename(self):
        self.ensure_one()
        return f'{self.name.replace("/", "_")}_facturae_signed.xml'

    def _l10n_es_edi_facturae_get_tax_period(self):
        self.ensure_one()
        if self.env['res.company'].fields_get(['account_tax_periodicity']):
            period_start, period_end = self.company_id._get_tax_closing_period_boundaries(self.date)
        else:
            period_start = date_utils.start_of(self.date, 'month')
            period_end = date_utils.end_of(self.date, 'month')

        return {'start':period_start, 'end':period_end}

    def _l10n_es_edi_facturae_get_refunded_invoices(self):
        self.env['account.partial.reconcile'].flush_model()
        invoices_refunded_mapping = {invoice.id: invoice.reversed_entry_id for invoice in self}

        queries = []
        for source_field, counterpart_field in (('debit', 'credit'), ('credit', 'debit')):
            queries.append(f'''
                SELECT
                    source_line.move_id AS source_move_id,
                    counterpart_line.move_id AS counterpart_move_id
                FROM account_partial_reconcile part
                JOIN account_move_line source_line ON source_line.id = part.{source_field}_move_id
                JOIN account_move_line counterpart_line ON counterpart_line.id = part.{counterpart_field}_move_id
                WHERE source_line.move_id IN %s AND counterpart_line.move_id != source_line.move_id
                GROUP BY source_move_id, counterpart_move_id
            ''')
        self._cr.execute(' UNION ALL '.join(queries), [tuple(self.ids)] * 2)
        payment_data = defaultdict(lambda: [])
        for row in self._cr.dictfetchall():
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

    @api.model
    def _l10n_es_edi_facturae_convert_computed_tax_to_template(self, computed_tax_dict):
        """ Helper to convert the tax dict from a _compute_taxes() into a dict usable in the template """
        tax = self.env["account.tax"].browse(computed_tax_dict["tax_id"])
        return {
            "tax_record": tax,
            "TaxRate": f'{abs(tax.amount):.3f}',
            "TaxableBase": {
                'TotalAmount': computed_tax_dict["base_amount_currency"],
                'EquivalentInEuros': computed_tax_dict["base_amount"],
            },
            "TaxAmount": {
                "TotalAmount": abs(computed_tax_dict["tax_amount_currency"]),
                "EquivalentInEuros": abs(computed_tax_dict["tax_amount"]),
            },
        }

    def _l10n_es_edi_facturae_inv_lines_to_items(self, conversion_rate=None):
        """
        Convert the invoice lines to a list of items required for the Facturae xml generation

        :param float conversion_rate: Conversion rate of the invoice, if needed
        :return: A tuple containing the Face items, the taxes and the invoice totals data.
        """
        self.ensure_one()
        items = []
        totals = {
            'total_gross_amount': 0.,
            'total_general_discounts': 0.,
            'total_general_surcharges': 0.,
            'total_taxes_withheld': 0.,
            'total_tax_outputs': 0.,
            'total_payments_on_account': 0.,
            'amounts_withheld': 0.,
        }
        taxes = []
        taxes_withheld = []
        for line in self.invoice_line_ids:
            if line.display_type in {'line_section', 'line_note'}:
                continue
            invoice_line_values = {}

            price_before_discount = line.currency_id.round(line.price_subtotal / (1 - line.discount / 100.0))
            discount = max(0., (price_before_discount - line.price_subtotal))
            surcharge = abs(min(0., (price_before_discount - line.price_subtotal)))
            totals['total_gross_amount'] += line.price_subtotal
            totals['total_general_discounts'] += discount
            totals['total_general_surcharges'] += surcharge
            base_line = self.env['account.tax']._convert_to_tax_base_line_dict(
                line, partner=line.partner_id, currency=line.currency_id, product=line.product_id, taxes=line.tax_ids,
                price_unit=line.price_unit, quantity=line.quantity, discount=line.discount, account=line.account_id,
                price_subtotal=line.price_subtotal, is_refund=line.is_refund, rate=conversion_rate
            )

            taxes_computed = self.env['account.tax']._compute_taxes([base_line])
            taxes_withheld_computed = [tax for tax in taxes_computed["tax_lines_to_add"] if tax["tax_amount"] < 0]
            taxes_normal_computed = [tax for tax in taxes_computed["tax_lines_to_add"] if tax["tax_amount"] >= 0]

            taxes_output = [self._l10n_es_edi_facturae_convert_computed_tax_to_template(tax) for tax in taxes_normal_computed]
            totals['total_tax_outputs'] += sum((abs(tax["tax_amount"]) for tax in taxes_normal_computed))

            tax_withheld_output = [self._l10n_es_edi_facturae_convert_computed_tax_to_template(tax) for tax in taxes_withheld_computed]
            totals['total_taxes_withheld'] += sum((abs(tax["tax_amount"]) for tax in taxes_withheld_computed))

            invoice_line_values.update({
                'ItemDescription': line.name,
                'Quantity': line.quantity,
                'UnitOfMeasure': line.product_uom_id.l10n_es_edi_facturae_uom_code,
                'UnitPriceWithoutTax': line.currency_id.round(price_before_discount / line.quantity if line.quantity else 0.),
                'TotalCost': price_before_discount,
                'DiscountsAndRebates': [{
                    'DiscountReason': '',
                    'DiscountRate': f'{line.discount:.2f}',
                    'DiscountAmount': discount
                }, ] if discount != 0. else [],
                'Charges': [{
                    'ChargeReason': '',
                    'ChargeRate': f'{max(0, -line.discount):.2f}',
                    'ChargeAmount': surcharge,
                }, ] if surcharge != 0. else [],
                'GrossAmount': line.price_subtotal,
                'TaxesOutputs': taxes_output,
                'TaxesWithheld': tax_withheld_output,
            })
            items.append(invoice_line_values)
            taxes += taxes_output
            taxes_withheld += tax_withheld_output
        return items, taxes, taxes_withheld, totals

    def _l10n_es_edi_facturae_export_facturae(self):
        """
        Produce the Facturae XML data for the invoice.

        :return: (data needed to render the full template, data needed to render the signature template)
        """
        self.ensure_one()
        company = self.company_id
        partner = self.commercial_partner_id

        if not company.vat:
            raise UserError(_('The company needs a set tax identification number or VAT number'))
        if not partner.vat:
            raise UserError(_('The partner needs a set tax identification number or VAT number'))
        if self.move_type == "entry":
            return False

        eur_curr = self.env['res.currency'].search([('name', '=', 'EUR')])
        inv_curr = self.currency_id
        legal_literals = self.narration.striptags() if self.narration else False
        legal_literals = legal_literals.split(";") if legal_literals else False

        partner_name = {'firstname': 'UNKNOWN', 'surname': 'UNKNOWN', 'surname2': ''}
        if not partner.is_company:
            name_split = [part for part in partner.name.replace(', ', ' ').split(' ') if part]
            if len(name_split) > 2:
                partner_name['firstname'] = ' '.join(name_split[:-2])
                partner_name['surname'], partner_name['surname2'] = name_split[-2:]
            elif len(name_split) == 2:
                partner_name['firstname'] = ' '.join(name_split[:-1])
                partner_name['surname'] = name_split[-1]

        invoice_issuer_signature_type = 'supplier' if self.move_type == 'out_invoice' else 'customer'
        need_conv = bool(inv_curr != eur_curr)
        conversion_rate = abs(self.amount_total_in_currency_signed / self.amount_total_signed) if self.amount_total_signed else 0.
        total_outst_am_in_currency = abs(self.amount_total_in_currency_signed)
        total_outst_am = abs(self.amount_total_signed)
        total_exec_am_in_currency = abs(self.amount_total_in_currency_signed)
        total_exec_am = abs(self.amount_total_signed)
        items, taxes, taxes_withheld, totals = self._l10n_es_edi_facturae_inv_lines_to_items(conversion_rate)
        template_values = {
            'self_party': company.partner_id,
            'self_party_country_code': COUNTRY_CODE_MAP[company.country_id.code],
            'other_party': partner,
            'other_party_country_code': COUNTRY_CODE_MAP[partner.country_id.code],
            'other_party_phone': partner.phone.translate(PHONE_CLEAN_TABLE) if partner.phone else False,
            'other_party_name': partner_name,
            'is_outstanding': self.move_type.startswith('out_'),
            'float_repr': float_repr,
            'file_currency': inv_curr,
            'eur': eur_curr,
            'conversion_needed': need_conv,
            'refund_multiplier': -1 if self.move_type.endswith('refund') else 1,

            'Modality': 'I',
            'BatchIdentifier': self.name,
            'InvoicesCount': 1,
            'TotalInvoicesAmount': {
                'TotalAmount': abs(self.amount_total_in_currency_signed),
                'EquivalentInEuros': abs(self.amount_total_signed),
            },
            'TotalOutstandingAmount': {
                'TotalAmount': abs(total_outst_am_in_currency),
                'EquivalentInEuros': abs(total_outst_am),
            },
            'TotalExecutableAmount': {
                'TotalAmount': total_exec_am_in_currency,
                'EquivalentInEuros': total_exec_am,
            },
            'InvoiceCurrencyCode': inv_curr.name,
            'Invoices': [{
                'invoice_record': self,
                'invoice_currency': inv_curr,
                'InvoiceDocumentType': 'FC',
                'InvoiceClass': 'OO',
                'Corrective': self._l10n_es_edi_facturae_get_corrective_data(),
                'InvoiceIssueData': {
                    'ExchangeRateDetails': need_conv,
                    'ExchangeRate': f"{round(conversion_rate, 4):.4f}",
                    'LanguageName': self._context.get('lang', 'en_US').split('_')[0],
                },
                'TaxOutputs': taxes,
                'TaxesWithheld': taxes_withheld,
                'TotalGrossAmount': totals['total_gross_amount'],
                'TotalGeneralDiscounts': totals['total_general_discounts'],
                'TotalGeneralSurcharges': totals['total_general_surcharges'],
                'TotalGrossAmountBeforeTaxes': totals['total_gross_amount'] - totals['total_general_discounts'] + totals['total_general_surcharges'],
                'TotalTaxOutputs': totals['total_tax_outputs'],
                'TotalTaxesWithheld': totals['total_taxes_withheld'],
                'PaymentsOnAccount': [],
                'TotalOutstandingAmount': total_outst_am_in_currency,
                'InvoiceTotal': abs(self.amount_total_in_currency_signed),
                'TotalPaymentsOnAccount': totals['total_payments_on_account'],
                'AmountsWithheld': {
                    'WithholdingReason': '',
                    'WithholdingRate': False,
                    'WithholdingAmount': totals['amounts_withheld'],
                } if totals['amounts_withheld'] else False,
                'TotalExecutableAmount': total_exec_am_in_currency,
                'Items': items,
                'PaymentDetails': [],
                'LegalLiterals': legal_literals,
            }],
        }
        signature_values = {'SigningTime': '', 'SignerRole': invoice_issuer_signature_type, }
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
        certificate = self.env['l10n_es_edi_facturae.certificate'].search([("company_id", '=', company.id)], limit=1)

        try:
            xml_content = certificate._sign_xml(xml_content, signature_values)
        except ValueError:
            raise UserError(_('No valid certificate found for this company, Facturae EDI file will not be signed.\n'))
        return xml_content

import re

from collections import defaultdict
from markupsafe import Markup

from odoo import fields, models, api, _, Command
from odoo.exceptions import UserError
from odoo.tools import float_repr, date_utils
from odoo.tools.xml_utils import cleanup_xml_node, find_xml_value

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

    def _l10n_es_edi_facturae_get_default_enable(self):
        self.ensure_one()
        return not self.invoice_pdf_report_id \
            and not self.l10n_es_edi_facturae_xml_id \
            and not self.l10n_es_is_simplified \
            and self.is_invoice(include_receipts=True) \
            and (self.partner_id.is_company or self.partner_id.vat) \
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
        invoices_refunded_mapping = {invoice.id: invoice.reversed_entry_id.id for invoice in self}

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

    def _l10n_es_edi_facturae_convert_payment_terms_to_installments(self):
        """
        Convert the payments terms to a list of <Installment> elements to be used in the
        <PaymentDetails> node of the Facturae XML generation.

        For now we only use the hardcoded '04' value (Credit Transfer).
        """
        self.ensure_one()
        installments = []
        if self.is_inbound() and self.partner_bank_id:
            for payment_term in self.line_ids.filtered(lambda l: l.display_type == 'payment_term').sorted('date_maturity'):
                installments.append({
                    'InstallmentDueDate': payment_term.date_maturity,
                    'InstallmentAmount': payment_term.amount_residual_currency,
                    'PaymentMeans': '04',  # Credit Transfer
                    'AccountToBeCredited': {
                        'IBAN': self.partner_bank_id.sanitized_acc_number,
                        'BIC': self.partner_bank_id.bank_bic,
                    },
                })
        return installments

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
        invoice_ref = self.ref[:20] if self.ref else False
        for line in self.invoice_line_ids:
            if line.display_type in {'line_section', 'line_note'}:
                continue
            invoice_line_values = {}

            tax_base_before_discount = self.env['account.tax']._convert_to_tax_base_line_dict(
                base_line=line,
                currency=line.currency_id,
                taxes=line.tax_ids,
                price_unit=line.price_unit,
                quantity=line.quantity,
            )
            tax_before_discount = self.env['account.tax']._compute_taxes([tax_base_before_discount])
            price_before_discount = sum(to_update['price_subtotal'] for _dummy, to_update in tax_before_discount['base_lines_to_update'])
            discount = max(0., (price_before_discount - line.price_subtotal))
            surcharge = abs(min(0., (price_before_discount - line.price_subtotal)))
            totals['total_gross_amount'] += line.price_subtotal
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

            receiver_transaction_reference = (
                line.sale_line_ids.order_id.client_order_ref[:20]
                if 'sale_line_ids' in line._fields and line.sale_line_ids.order_id.client_order_ref
                else invoice_ref
            )

            invoice_line_values.update({
                'ReceiverTransactionReference': receiver_transaction_reference,
                'FileReference': invoice_ref,
                'ReceiverContractReference': invoice_ref,
                'FileDate': fields.Date.context_today(self),
                'ItemDescription': line.name,
                'Quantity': line.quantity,
                'UnitOfMeasure': line.product_uom_id.l10n_es_edi_facturae_uom_code,
                'UnitPriceWithoutTax': line.currency_id.round(price_before_discount / line.quantity if line.quantity else 0.),
                'TotalCost': price_before_discount,
                'DiscountsAndRebates': [{
                    'DiscountReason': '/',
                    'DiscountRate': f'{line.discount:.2f}',
                    'DiscountAmount': discount
                }, ] if discount != 0. else [],
                'Charges': [{
                    'ChargeReason': '/',
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

        eur_curr = self.env['res.currency'].search([('name', '=', 'EUR')])
        inv_curr = self.currency_id
        legal_literals = self.narration.striptags() if self.narration else False
        legal_literals = legal_literals.split(";") if legal_literals else False

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
            'self_party_name': extract_party_name(company.partner_id),
            'other_party': partner,
            'other_party_country_code': COUNTRY_CODE_MAP[partner.country_id.code],
            'other_party_phone': partner.phone.translate(PHONE_CLEAN_TABLE) if partner.phone else False,
            'other_party_name': extract_party_name(partner),
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
                    'OperationDate': operation_date,
                    'ExchangeRateDetails': need_conv,
                    'ExchangeRate': f"{round(conversion_rate, 4):.4f}",
                    'LanguageName': self._context.get('lang', 'en_US').split('_')[0],
                    'ReceiverTransactionReference': self.ref[:20] if self.ref else False,
                    'FileReference': self.ref[:20] if self.ref else False,
                    'ReceiverContractReference': self.ref[:20] if self.ref else False,
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
                'PaymentDetails': self._l10n_es_edi_facturae_convert_payment_terms_to_installments(),
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

        errors = []
        try:
            xml_content = certificate._sign_xml(xml_content, signature_values)
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
        mail = partner_vals['email']
        country_code = partner_vals['country_code']

        partner = self.env['res.partner']._retrieve_partner(name=name, vat=vat, phone=phone, mail=mail)

        if not partner and name:
            partner_vals = {'name': name, 'email': mail, 'phone': phone}
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
                    logs.append(_("Could not retrieve the tax: %s %% for line '%s'.", tax_rate, line_vals.get('name', "")))

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

    def _generate_pdf_and_send_invoice(self, template, force_synchronous=True, allow_fallback_pdf=True, bypass_download=False, **kwargs):
        if self.company_id.country_code == "ES" and not self.company_id.l10n_es_edi_facturae_certificate_id:
            kwargs['l10n_es_edi_facturae_checkbox_xml'] = False
        return super()._generate_pdf_and_send_invoice(template, force_synchronous, allow_fallback_pdf, bypass_download, **kwargs)

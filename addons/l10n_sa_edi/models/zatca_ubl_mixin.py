"""
Common ZATCA EDI functionality shared between Account and POS modules.

This mixin provides base implementation for ZATCA-compliant UBL 2.1 XML generation
that can be used by both account.edi.xml.ubl_21.zatca and pos.edi.xml.ubl_21.zatca.
"""
import re
from base64 import b64encode
from hashlib import sha256

from lxml import etree

from odoo import fields, models
from odoo.tools.misc import file_path

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import FloatFmt

# ZATCA Tax Classification Constants
TAX_EXEMPTION_CODES = ['VATEX-SA-29', 'VATEX-SA-29-7', 'VATEX-SA-30']
TAX_ZERO_RATE_CODES = ['VATEX-SA-32', 'VATEX-SA-33', 'VATEX-SA-34-1', 'VATEX-SA-34-2', 'VATEX-SA-34-3', 'VATEX-SA-34-4', 'VATEX-SA-34-5', 'VATEX-SA-35', 'VATEX-SA-36', 'VATEX-SA-EDU', 'VATEX-SA-HEA']

# ZATCA Payment Means Codes (UN/ECE 4461)
PAYMENT_MEANS_CODE = {
    'bank': 42,      # Payment to bank account
    'card': 48,      # Bank card
    'cash': 10,      # In cash
    'transfer': 30,  # Credit transfer
    'unknown': 1,     # Instrument not defined
}


class ZatcaUblMixin(models.AbstractModel):
    """
    Common mixin for ZATCA EDI implementations.

    This provides shared functionality for generating ZATCA-compliant UBL 2.1 XML
    documents for both regular invoices (account.move) and POS orders (pos.order).
    """

    _name = 'zatca.ubl.mixin'
    _description = 'ZATCA UBL Mixin'

    # -------------------------------------------------------------------------
    # EXPORT
    # Methods here take a dict, vals
    # -------------------------------------------------------------------------

    def _ubl_add_values_document_type(self, vals):
        """
            Only use Invoice in ZATCA, even for credit and debit notes because we want the root
            tag of the document to be <Invoice>
        """
        self._define_document_type(vals, 'invoice')

    def _ubl_default_tax_category_grouping_key(self, base_line, tax_data, vals, currency):
        tax = tax_data and tax_data['tax']

        # Always ignore withholding taxes in the UBL
        if tax and tax.amount < 0:
            return None

        customer = vals['customer'].commercial_partner_id
        supplier = vals['supplier']
        amount_type = tax.amount_type if tax else 'percent'
        return {
            'tax_category_code': self._get_tax_category_code(customer, supplier, tax),
            **self._get_tax_exemption_reason(customer, supplier, tax),
            'percent': (tax.amount if tax else 0.0) if amount_type == 'percent' else None,
            'scheme_id': 'VAT',
            'is_withholding': False,
            'currency': currency,
        }

    def _ubl_tax_totals_node_grouping_key(self, base_line, tax_data, vals, currency):
        # Each tax category has its own TaxSubtotal.
        grouping_keys = super()._ubl_tax_totals_node_grouping_key(base_line, tax_data, vals, currency)
        if grouping_keys['tax_category_key']:
            grouping_keys['tax_subtotal_key'] = dict(grouping_keys['tax_category_key'])
        return grouping_keys

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document header nodes
    # -------------------------------------------------------------------------

    def _get_party_node(self, vals):
        partner = vals['partner']
        role = vals['role']
        commercial_partner = partner.commercial_partner_id

        party_node = {}

        if identification_number := self._get_partner_party_identification_number(commercial_partner):
            scheme_id = 'OTH' if commercial_partner.country_code != 'SA' else commercial_partner.l10n_sa_edi_additional_identification_scheme
            party_node['cac:PartyIdentification'] = {
                'cbc:ID': {
                    '_text': identification_number,
                    'schemeID': scheme_id,
                },
            }

        party_node.update({
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name},
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:RegistrationAddress': self._get_address_node({'partner': commercial_partner}),
                'cac:TaxScheme': {
                    'cbc:ID': {'_text': 'VAT'}
                }
            } if (role != 'customer' or partner.country_id.code == 'SA') and commercial_partner.vat and commercial_partner.vat != '/' else None,  # BR-KSA-46
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat} if commercial_partner.country_code == 'SA' else None,
                'cac:RegistrationAddress': self._get_address_node({'partner': commercial_partner}),
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {
                    '_text': re.sub(r"[^+\d]", '', partner.phone) if partner.phone else None,
                },
                'cbc:ElectronicMail': {'_text': partner.email},
            },
        })
        return party_node

    def _get_address_node(self, vals):
        partner = vals['partner']
        building_number = partner.l10n_sa_edi_building_number if partner._name == 'res.partner' else ''
        edi_plot_identification = partner.l10n_sa_edi_plot_identification if partner._name == 'res.partner' else ''

        return {
            'cbc:StreetName': {'_text': partner.street},
            'cbc:BuildingNumber': {'_text': building_number},
            'cbc:PlotIdentification': {'_text': edi_plot_identification},
            'cbc:CitySubdivisionName': {'_text': partner.street2},
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': partner.state_id.name},
            'cbc:CountrySubentityCode': {'_text': partner.state_id.code},
            'cac:AddressLine': None,
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': partner.country_id.code},
                'cbc:Name': {'_text': partner.country_id.name},
            },
        }

    def _get_partner_party_identification_number(self, partner):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        identification_number = partner.l10n_sa_edi_additional_identification_number
        vat = re.sub(r'[^a-zA-Z0-9]', '', partner.vat or "")
        if partner.country_code != "SA":
            identification_number = vat or identification_number
        elif partner.l10n_sa_edi_additional_identification_scheme == 'TIN':
            # according to ZATCA, the TIN number is always the first 10 digits of the VAT number
            identification_number = partner._l10n_sa_get_tin_from_vat(vat)
        return identification_number

    def _ubl_add_accounting_supplier_party_node(self, vals):
        vals['document_node']['cac:AccountingSupplierParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'}),
        }

    def _ubl_add_accounting_customer_party_node(self, vals):
        vals['document_node']['cac:AccountingCustomerParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'}),
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document amount nodes
    # -------------------------------------------------------------------------

    def _ubl_add_tax_totals_nodes(self, vals):
        super()._ubl_add_tax_totals_nodes(vals)

        # The first TaxTotal is in the document currency, the second one only contains the tax amount in the
        # company currency, even if both currencies are the same.
        document_node = vals['document_node']
        currency = vals['currency']
        company_currency = vals['company_currency']
        tax_total_nodes = document_node['cac:TaxTotal']
        tax_total_node = next((node for node in tax_total_nodes if node['_currency'] == currency), None) or {
            '_currency': currency,
            'cbc:TaxAmount': {
                '_text': FloatFmt(0.0, min_dp=currency.decimal_places),
                'currencyID': currency.name,
            },
            'cac:TaxSubtotal': [],
        }
        if currency == company_currency:
            company_tax_amount = tax_total_node['cbc:TaxAmount']['_text']
        else:
            company_tax_total_node = next((node for node in tax_total_nodes if node['_currency'] == company_currency), None)
            company_tax_amount = company_tax_total_node['cbc:TaxAmount']['_text'] if company_tax_total_node else 0.0
        document_node['cac:TaxTotal'] = [
            tax_total_node,
            {
                # No '_currency' so that it isn't summed in the monetary totals.
                '_currency': None,
                'cbc:TaxAmount': {
                    '_text': FloatFmt(company_tax_amount, min_dp=company_currency.decimal_places),
                    'currencyID': company_currency.name,
                },
            },
        ]

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document line nodes
    # -------------------------------------------------------------------------

    def _ubl_add_line_allowance_charge_nodes(self, vals):
        super()._ubl_add_line_allowance_charge_nodes(vals)
        self._ubl_add_line_allowance_charge_nodes_for_discount(vals)

    def _ubl_get_line_allowance_charge_discount_node(self, vals, discount_values):
        currency = discount_values['currency']
        return {
            '_currency': currency,
            'cbc:ChargeIndicator': {'_text': 'true' if discount_values['is_charge'] else 'false'},
            'cbc:AllowanceChargeReasonCode': {'_text': '95'},
            'cbc:Amount': {
                '_text': FloatFmt(abs(discount_values['amount']), min_dp=currency.decimal_places, max_dp=currency.decimal_places),
                'currencyID': currency.name,
            },
        }

    def _ubl_add_line_tax_totals_nodes(self, vals):
        AccountTax = self.env['account.tax']
        base_line = vals['line_vals']['base_line']
        currency = base_line['currency_id']
        aggregated_values = AccountTax._aggregate_base_line_tax_details(
            base_line=base_line,
            grouping_function=lambda base_line, tax_data: self._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency),
        )
        total_tax_amount = sum(values['tax_amount_currency'] for grouping_key, values in aggregated_values.items() if grouping_key)
        total_base_amount = sum(values['base_amount_currency'] for grouping_key, values in aggregated_values.items() if grouping_key)

        vals['line_node']['cac:TaxTotal'] = [{
            'cbc:TaxAmount': {
                '_text': FloatFmt(total_tax_amount, min_dp=currency.decimal_places, max_dp=currency.decimal_places),
                'currencyID': currency.name,
            },
            'cbc:RoundingAmount': {
                # This should simply contain the net (base + tax) amount for the line.
                '_text': FloatFmt(total_base_amount + total_tax_amount, min_dp=currency.decimal_places, max_dp=currency.decimal_places),
                'currencyID': currency.name,
            },
            # No TaxSubtotal: BR-KSA-80: only downpayment lines should have a tax subtotal breakdown.
        }]

    def _ubl_add_line_item_name_description_nodes(self, vals):
        item_node = vals['item_node']
        base_line = vals['line_vals']['base_line']
        product = base_line['product_id']
        line_name = base_line['record'] and base_line['record'].name
        line_name = line_name and line_name.replace('\n', ' ')

        item_node['cbc:Description'] = {'_text': line_name or product.description_sale}
        item_node['cbc:Name'] = {'_text': product.name or line_name}

    def _ubl_add_line_item_identification_nodes(self, vals):
        super()._ubl_add_line_item_identification_nodes(vals)
        product = vals['line_vals']['base_line']['product_id']
        vals['item_node']['cac:SellersItemIdentification'] = {
            'cbc:ID': {'_text': product.code or product.default_code},
        }

    def _ubl_add_line_item_commodity_classification_nodes(self, vals):
        vals['item_node']['cac:CommodityClassification'] = []

    def _ubl_get_line_item_node_classified_tax_category_node(self, vals, tax_category):
        return self._ubl_get_tax_category_node(vals, tax_category)

    def _ubl_add_line_extension_amount_node(self, vals, in_foreign_currency=True):
        # The LineExtensionAmount must match the line amounts reported in the TaxTotal, global rounding included.
        base_line = vals['line_vals']['base_line']
        currency = base_line['currency_id']
        tax_details = base_line['tax_details']
        vals['line_node']['cbc:LineExtensionAmount'] = {
            '_text': FloatFmt(
                tax_details['total_excluded_currency'] + tax_details['delta_total_excluded_currency'],
                min_dp=currency.decimal_places,
                max_dp=currency.decimal_places,
            ),
            'currencyID': currency.name,
        }

    def _ubl_add_line_price_node(self, vals, in_foreign_currency=True):
        """
        Use 10 decimal places for PriceAmount to satisfy ZATCA validation BR-KSA-EN16931-11, computed from the gross
        subtotal rounded to the currency so that it matches the LineExtensionAmount.
        """
        base_line = vals['line_vals']['base_line']
        currency = base_line['currency_id']
        discount_factor = 1 - (base_line['discount'] / 100.0)
        if not base_line['quantity'] or not discount_factor:
            gross_price_unit = base_line['price_unit']
        else:
            gross_subtotal = currency.round(base_line['tax_details']['raw_total_excluded_currency'] / discount_factor)
            gross_price_unit = gross_subtotal / base_line['quantity']

        vals['line_node']['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': round(gross_price_unit, 10),
                'currencyID': currency.name,
            },
        }

    # -------------------------------------------------------------------------
    # EXPORT: Helpers for hash generation
    # -------------------------------------------------------------------------

    def _l10n_sa_get_namespaces(self):
        """
        Namespaces used in the final UBL declaration, required to canonalize the finalized XML document of the Invoice
        """
        return {
            'cac': 'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2',
            'cbc': 'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2',
            'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2',
            'sig': 'urn:oasis:names:specification:ubl:schema:xsd:CommonSignatureComponents-2',
            'sac': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureAggregateComponents-2',
            'sbc': 'urn:oasis:names:specification:ubl:schema:xsd:SignatureBasicComponents-2',
            'ds': 'http://www.w3.org/2000/09/xmldsig#',
            'xades': 'http://uri.etsi.org/01903/v1.3.2#',
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document allowance charge nodes
    # -------------------------------------------------------------------------

    def _is_document_allowance_charge(self, base_line):
        return base_line['special_type'] == 'early_payment' or base_line['tax_details']['total_excluded_currency'] < 0

    def _ubl_add_allowance_charge_nodes(self, vals):
        """
        Charge Reasons & Codes (As per ZATCA):
        https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5189.htm
        As far as ZATCA is concerned, we calculate Allowance/Charge vals for global discounts as
        a document level allowance, and we do not include any other charges or allowances.
        """
        AccountTax = self.env['account.tax']
        super()._ubl_add_allowance_charge_nodes(vals)
        self._ubl_add_allowance_charge_nodes_early_payment_discount(vals)

        currency = vals['currency']
        nodes = vals['document_node']['cac:AllowanceCharge']
        for base_line in vals['base_lines']:
            if self._ubl_is_early_payment_base_line(base_line) or not self._is_document_allowance_charge(base_line):
                continue

            aggregated_values = AccountTax._aggregate_base_line_tax_details(
                base_line=base_line,
                grouping_function=lambda base_line, tax_data: self._ubl_default_tax_category_grouping_key(base_line, tax_data, vals, currency),
            )
            nodes.append({
                '_currency': currency,
                'cbc:ChargeIndicator': {'_text': 'false'},
                'cbc:AllowanceChargeReasonCode': {'_text': '95'},
                'cbc:AllowanceChargeReason': {'_text': 'Discount'},
                'cbc:Amount': {
                    '_text': FloatFmt(abs(base_line['tax_details']['total_excluded_currency']), min_dp=2, max_dp=2),
                    'currencyID': currency.name,
                },
                'cac:TaxCategory': [
                    self._ubl_get_tax_category_node(vals, grouping_key)
                    for grouping_key in aggregated_values
                    if grouping_key
                ],
            })

    # -------------------------------------------------------------------------
    # Tax Category and Exemption
    # -------------------------------------------------------------------------

    def _get_tax_category_code(self, customer, supplier, tax):
        """
        Get ZATCA tax category code based on tax configuration.

        ZATCA Tax Categories:
        - S: Standard rated
        - E: Exempted (VATEX-SA-29, 29-7, 30)
        - Z: Zero rated with VAT (VATEX-SA-32 through 36, EDU, HEA)
        - O: Not subject to VAT

        :param customer: res.partner - Customer/buyer
        :param supplier: res.partner - Supplier/seller
        :param tax: account.tax - Tax record
        :return: str - Tax category code
        """
        if supplier.country_id.code == 'SA':
            if tax and tax.amount != 0:
                return 'S'
            if tax and tax.ubl_cii_tax_exemption_reason_code in TAX_EXEMPTION_CODES:
                return 'E'
            if tax and tax.ubl_cii_tax_exemption_reason_code in TAX_ZERO_RATE_CODES:
                return 'Z'

            return 'O'
        return super()._get_tax_category_code(customer, supplier, tax)

    def _get_tax_exemption_reason(self, customer, supplier, tax):
        """
        Get tax exemption reason code and description for ZATCA.

        :param customer: res.partner - Customer/buyer
        :param supplier: res.partner - Supplier/seller
        :param tax: account.tax - Tax record
        :return: dict - Contains tax_exemption_reason_code and tax_exemption_reason
        """
        if supplier.country_id.code != 'SA':
            return super()._get_tax_exemption_reason(customer, supplier, tax)

        if tax and tax.amount == 0:
            exemption_reason_by_code = dict(tax._fields["ubl_cii_tax_exemption_reason_code"]._description_selection(self.env))
            code = tax.ubl_cii_tax_exemption_reason_code or "VATEX-SA-OOS"
            exemption_reason = exemption_reason_by_code[code].split(code)[1].lstrip() if code else "Not subject to VAT"

            if code == "VATEX-SA-OOS" and (tax_exemption_reason := tax.ubl_cii_tax_exemption_reason):
                # In case of VATEX-SA-OOS we allow the user to use his own defined exemption reason
                exemption_reason = tax_exemption_reason

            return {
                'tax_exemption_reason_code': code,
                'tax_exemption_reason': exemption_reason,
            }

        return {
            'tax_exemption_reason_code': None,
            'tax_exemption_reason': None,
        }

    # -------------------------------------------------------------------------
    # XML Hash Generation
    # -------------------------------------------------------------------------

    def _l10n_sa_generate_invoice_xml_sha(self, xml_content):
        """
        Generate SHA256 hash of transformed and canonicalized invoice XML.

        Process:
        1. Parse XML content
        2. Transform using XSLT to remove signatures
        3. Canonicalize using c14n method
        4. Hash using SHA256

        :param xml_content: bytes or str - XML content
        :return: hashlib.sha256 object
        """
        def _canonicalize_xml(content):
            """Canonicalize XML using c14n method."""
            return etree.tostring(
                content,
                method="c14n",
                exclusive=False,
                with_comments=False,
                inclusive_ns_prefixes=self._l10n_sa_get_namespaces(),
            )

        def _transform_and_canonicalize_xml(content):
            """Transform XML to remove signatures then canonicalize."""
            invoice_xsl = etree.parse(file_path('l10n_sa_edi/data/pre-hash_invoice.xsl'))
            transform = etree.XSLT(invoice_xsl)
            return _canonicalize_xml(transform(content))

        root = etree.fromstring(xml_content)
        transformed_xml = _transform_and_canonicalize_xml(root)
        return sha256(transformed_xml)

    def _l10n_sa_generate_invoice_xml_hash(self, xml_content, mode='hexdigest'):
        """
        Generate the b64 encoded sha256 hash of a given xml string:
            - First: Transform the xml content using a pre-hash_invoice.xsl file
            - Second: Canonicalize the transformed xml content using the c14n method
            - Third: hash the canonicalized content using the sha256 algorithm then encode it into b64 format
        """
        xml_sha = self._l10n_sa_generate_invoice_xml_sha(xml_content)
        if mode == 'hexdigest':
            xml_hash = xml_sha.hexdigest().encode()
        elif mode == 'digest':
            xml_hash = xml_sha.digest()
        return b64encode(xml_hash)

    # -------------------------------------------------------------------------
    # Common Filename Generation
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, record):
        """
            Generate the name of the invoice XML file according to ZATCA business rules:
            Seller Vat Number (BT-31), Date (BT-2), Time (KSA-25), Invoice Number (BT-1)
        """
        vat = record.company_id.partner_id.commercial_partner_id.vat
        record_number = re.sub(r'[^a-zA-Z0-9 -]+', '-', record.name)
        record_date = fields.Datetime.context_timestamp(self.with_context(tz='Asia/Riyadh'), record.l10n_sa_confirmation_datetime)
        file_name = f"{vat}_{record_date.strftime('%Y%m%dT%H%M%S')}_{record_number}"
        file_format = self.env.context.get('l10n_sa_file_format', 'xml')
        if file_format:
            file_name = f'{file_name}.{file_format}'
        return file_name

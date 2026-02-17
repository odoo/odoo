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

    def _add_invoice_config_vals(self, vals):
        """
            Only use Invoice in ZATCA, even for credit and debit notes because we want the root
            tag of the document to be <Invoice>
        """
        super()._add_invoice_config_vals(vals)
        vals['document_type'] = 'invoice'

    def _add_document_tax_grouping_function_vals(self, vals):
        # Always ignore withholding taxes in the UBL
        def total_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            if tax and tax.amount < 0:
                return None
            return True

        def tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']

            # Ignore withholding taxes
            if tax and tax.amount < 0:
                return None
            return {
                'tax_category_code': self._get_tax_category_code(vals['customer'].commercial_partner_id, vals['supplier'], tax),
                **self._get_tax_exemption_reason(vals['customer'].commercial_partner_id, vals['supplier'], tax),
                'amount': tax.amount if tax else 0.0,
                'amount_type': tax.amount_type if tax else 'percent',
            }

        vals['total_grouping_function'] = total_grouping_function
        vals['tax_grouping_function'] = tax_grouping_function

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document header nodes
    # -------------------------------------------------------------------------

    def _get_party_node(self, vals):
        partner = vals['partner']
        role = vals['role']
        commercial_partner = partner.commercial_partner_id

        party_node = {}

        if identification_number := self._get_partner_party_identification_number(commercial_partner):
            party_node['cac:PartyIdentification'] = {
                'cbc:ID': {
                    '_text': identification_number,
                    'schemeID': commercial_partner.l10n_sa_edi_additional_identification_scheme,
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
            identification_number = vat
        elif partner.l10n_sa_edi_additional_identification_scheme == 'TIN':
            # according to ZATCA, the TIN number is always the first 10 digits of the VAT number
            identification_number = vat[:10]
        return identification_number

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document amount nodes
    # -------------------------------------------------------------------------

    def _add_document_tax_total_nodes(self, document_node, vals):
        super()._add_document_tax_total_nodes(document_node, vals)

        document_node['cac:TaxTotal'] = [document_node['cac:TaxTotal']]

        self._add_tax_total_node_in_company_currency(document_node, vals)
        document_node['cac:TaxTotal'][1]['cac:TaxSubtotal'] = None

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document line nodes
    # -------------------------------------------------------------------------

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        total_tax_amount = sum(
            values['tax_amount_currency']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key
        )
        total_base_amount = sum(
            values['base_amount_currency']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key
        )
        total_amount = total_base_amount + total_tax_amount

        line_node['cac:TaxTotal'] = {
            'cbc:TaxAmount': {
                '_text': self.format_float(total_tax_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:RoundingAmount': {
                # This should simply contain the net (base + tax) amount for the line.
                '_text': self.format_float(total_amount, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            # No TaxSubtotal: BR-KSA-80: only downpayment lines should have a tax subtotal breakdown.
        }

    def _add_document_line_item_nodes(self, line_node, vals):
        super()._add_document_line_item_nodes(line_node, vals)
        product = vals['base_line']['product_id']
        line_node['cac:Item']['cac:SellersItemIdentification'] = {
            'cbc:ID': {'_text': product.code or product.default_code},
        }

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        line_node['cac:Item']['cac:ClassifiedTaxCategory'] = [
            self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
            for grouping_key in aggregated_tax_details
            if grouping_key
        ]

    def _add_document_line_price_nodes(self, line_node, vals):
        """
        Use 10 decimal places for PriceAmount to satisfy ZATCA validation BR-KSA-EN16931-11
        """
        currency_suffix = vals['currency_suffix']
        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': round(vals[f'gross_price_unit{currency_suffix}'], 10),
                'currencyID': vals['currency_name'],
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

    def _get_document_allowance_charge_node(self, vals):
        """
        Charge Reasons & Codes (As per ZATCA):
        https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5189.htm
        As far as ZATCA is concerned, we calculate Allowance/Charge vals for global discounts as
        a document level allowance, and we do not include any other charges or allowances.
        """
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])

        base_amount_currency = base_line['tax_details']['total_excluded_currency']
        if base_line['special_type'] == 'early_payment':
            return super()._get_document_allowance_charge_node(vals)
        if base_amount_currency < 0:
            return {
                'cbc:ChargeIndicator': {'_text': 'false'},
                'cbc:AllowanceChargeReasonCode': {'_text': '95'},
                'cbc:AllowanceChargeReason': {'_text': 'Discount'},
                'cbc:Amount': {
                    '_text': self.format_float(abs(base_amount_currency), 2),
                    'currencyID': vals['currency_id'].name,
                },
                'cac:TaxCategory': [
                    self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
                    for grouping_key in aggregated_tax_details
                    if grouping_key
                ],
            }

        return {}
    # -------------------------------------------------------------------------
    # EXPORT: Templates for document header nodes helpers
    # -------------------------------------------------------------------------

    def _set_delivery_nodes(self, document_node, record):
        if 'cac:Delivery' not in document_node:
            return

        issue_date = fields.Datetime.context_timestamp(
            self.with_context(tz='Asia/Riyadh'),
            record.l10n_sa_confirmation_datetime,
        )
        if document_node['cac:Delivery']['cac:DeliveryLocation']:
            document_node['cac:Delivery']['cac:DeliveryLocation'] = None

        if not document_node['cac:Delivery']['cbc:ActualDeliveryDate']['_text']:
            document_node['cac:Delivery']['cbc:ActualDeliveryDate'] = {'_text': issue_date}

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
            if tax and tax.l10n_sa_exemption_reason_code in TAX_EXEMPTION_CODES:
                return 'E'
            if tax and tax.l10n_sa_exemption_reason_code in TAX_ZERO_RATE_CODES:
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
            exemption_reason_by_code = dict(tax._fields["l10n_sa_exemption_reason_code"]._description_selection(self.env))
            code = tax.l10n_sa_exemption_reason_code
            return {
                'tax_exemption_reason_code': code or "VATEX-SA-OOS",
                'tax_exemption_reason': (
                    exemption_reason_by_code[code].split(code)[1].lstrip()
                    if code else "Not subject to VAT"
                ),
            }

        return {
            'tax_exemption_reason_code': None,
            'tax_exemption_reason': None,
        }

    # -------------------------------------------------------------------------
    # Payment Means
    # -------------------------------------------------------------------------

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        """ Override to include/update values specific to ZATCA's UBL 2.1 specs """
        super()._add_invoice_payment_means_nodes(document_node, vals)
        payment_means_node = document_node['cac:PaymentMeans']
        invoice = vals['invoice']

        payment_means_node['cbc:PaymentMeansCode'] = {
            '_text': PAYMENT_MEANS_CODE.get(
                invoice._l10n_sa_get_payment_means_code(),
                PAYMENT_MEANS_CODE['unknown'],
            ),
            'listID': 'UN/ECE 4461',
        }
        payment_means_node['cbc:InstructionNote'] = {'_text': invoice._l10n_sa_get_adjustment_reason()}

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

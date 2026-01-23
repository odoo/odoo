from datetime import datetime

from pytz import UTC

from odoo import api, models
from odoo.addons.l10n_my_edi.models.account_edi_xml_ubl_my import COUNTRY_CODE_MAP


class AccountEdiXmlUBLMyInvoisMY(models.AbstractModel):
    _inherit = "account.edi.xml.ubl_myinvois_my"

    # -----------------------
    # CRUD, inherited methods
    # -----------------------

    def _add_myinvois_document_monetary_total_vals(self, vals):
        super()._add_myinvois_document_monetary_total_vals(vals)

        myinvois_document = vals["myinvois_document"]
        if myinvois_document.pos_order_ids:
            # Add the total amount paid.
            vals.update({
                'total_paid_amount': sum(order.amount_paid / order.currency_rate for order in myinvois_document.pos_order_ids),
                'total_paid_amount_currency': sum(myinvois_document.pos_order_ids.mapped('amount_paid')),
            })

    @api.model
    def _l10n_my_edi_get_refund_details(self, invoice):
        """
        Override in order to get the original document from the PoS order in case of refund of a
        PoS consolidated invoice.

        Note that by design, we consider that a refund done in a PoS is an actual refund and never a
        credit note.
        :param invoice: The credit note for which we want to get the refunded document.
        :return: A tuple, where the first parameter indicates if this credit note is a refund and the second the credited/refunded document.
        """
        if not invoice.pos_order_ids:
            return super()._l10n_my_edi_get_refund_details(invoice)  # the existing logic is enough.

        refunded_order = invoice.pos_order_ids[0].refunded_order_id
        consolidated_invoices = refunded_order._get_active_consolidated_invoice()
        return True, consolidated_invoices

    # Consolidated invoice export

    def _get_consolidated_invoice_node(self, vals):
        self._add_consolidated_invoice_config_vals(vals)
        self._add_consolidated_invoice_base_lines_vals(vals)
        self._setup_base_lines(vals)
        self._add_document_currency_vals(vals)
        self._add_document_tax_grouping_function_vals(vals)
        self._setup_base_lines(vals)
        self._add_consolidated_invoice_monetary_total_vals(vals)

        document_node = {}
        self._add_consolidated_invoice_header_nodes(document_node, vals)
        self._add_consolidated_invoice_accounting_supplier_party_nodes(document_node, vals)
        self._add_consolidated_invoice_accounting_customer_party_nodes(document_node, vals)

        self._add_document_allowance_charge_nodes(document_node, vals)
        self._add_document_tax_total_nodes(document_node, vals)
        self._add_consolidated_invoice_monetary_total_nodes(document_node, vals)
        self._add_consolidated_invoice_line_nodes(document_node, vals)
        return document_node

    def _add_consolidated_invoice_config_vals(self, vals):
        consolidated_invoice = vals['consolidated_invoice']
        supplier = consolidated_invoice.company_id.partner_id.commercial_partner_id
        # Use a search and not a ref in case the user create their own partner/...
        general_public_customer = self.env["res.partner"].search(
            domain=[
                *self.env['res.partner']._check_company_domain(consolidated_invoice.company_id),
                '|',
                ('vat', '=', 'EI00000000010'),
                ('l10n_my_edi_malaysian_tin', '=', 'EI00000000010'),
            ],
            limit=1,
        )

        vals.update({
            'document_type': 'invoice',
            'document_type_code': '01',

            'document_name': consolidated_invoice.name,

            'supplier': supplier,
            'customer': general_public_customer,
            'partner_shipping': None,

            'company': consolidated_invoice.company_id,
            'currency_id': consolidated_invoice.currency_id,
            'company_currency_id': consolidated_invoice.company_currency_id,

            'use_company_currency': False,
            'fixed_taxes_as_allowance_charges': True,
            'export_custom_form_reference': consolidated_invoice.myinvois_custom_form_reference,
        })

    def _add_consolidated_invoice_base_lines_vals(self, vals):
        AccountTax = self.env['account.tax']
        consolidated_invoice = vals['consolidated_invoice']
        consolidated_base_lines = []
        orders_per_line = next(iter(consolidated_invoice._separate_orders_in_lines(consolidated_invoice.pos_order_ids).values()))  # Only one config in a same consolidated invoice
        tax_data_fields = (
            'raw_base_amount_currency', 'raw_base_amount', 'raw_tax_amount_currency', 'raw_tax_amount',
            'base_amount_currency', 'base_amount', 'tax_amount_currency', 'tax_amount',
        )
        for index, orders in enumerate(orders_per_line):
            base_lines = []
            for order in orders:
                order_base_lines = order._prepare_tax_base_line_values()
                AccountTax._add_tax_details_in_base_lines(order_base_lines, consolidated_invoice.company_id)
                AccountTax._round_base_lines_tax_details(order_base_lines, consolidated_invoice.company_id)
                base_lines += order_base_lines

            # Aggregate the base lines into one.
            new_tax_details = {
                'raw_total_excluded_currency': 0.0,
                'total_excluded_currency': 0.0,
                'raw_total_excluded': 0.0,
                'total_excluded': 0.0,
                'raw_total_included_currency': 0.0,
                'total_included_currency': 0.0,
                'raw_total_included': 0.0,
                'total_included': 0.0,
                'delta_total_excluded_currency': 0.0,
                'delta_total_excluded': 0.0,
            }
            new_taxes_data_map = {}

            taxes = self.env['account.tax']
            for base_line in base_lines:
                tax_details = base_line['tax_details']
                sign = -1 if base_line['is_refund'] else 1
                for key in new_tax_details:
                    new_tax_details[key] += sign * tax_details[key]
                for tax_data in tax_details['taxes_data']:
                    tax = tax_data['tax']
                    taxes |= tax
                    if tax in new_taxes_data_map:
                        for key in tax_data_fields:
                            new_taxes_data_map[tax][key] += sign * tax_data[key]
                    else:
                        new_taxes_data_map[tax] = dict(tax_data)
                        for key in tax_data_fields:
                            new_taxes_data_map[tax][key] = sign * tax_data[key]

            total_amount_discounted = new_tax_details['total_excluded'] + new_tax_details['delta_total_excluded']
            total_amount_discounted_currency = new_tax_details['total_excluded_currency'] + new_tax_details['delta_total_excluded_currency']
            total_amount = total_amount_currency = 0.0
            for base_line in base_lines:
                sign = -1 if base_line["is_refund"] else 1
                discount_factor = 1 - (base_line['discount'] / 100.0)
                if discount_factor:
                    total_amount += sign * (base_line['tax_details']['raw_total_excluded'] / discount_factor)
                    total_amount_currency += sign * (base_line['tax_details']['raw_total_excluded_currency'] / discount_factor)
                else:
                    total_amount += sign * ((base_line['price_unit'] / base_line['rate']) * base_line['quantity'])
                    total_amount_currency += sign * (base_line['price_unit'] * base_line['quantity'])

            new_base_line = AccountTax._prepare_base_line_for_taxes_computation(
                {},
                tax_ids=taxes,
                price_unit=total_amount_currency,
                discount_amount=total_amount - total_amount_discounted,
                discount_amount_currency=total_amount_currency - total_amount_discounted_currency,
                quantity=1.0,
                currency_id=consolidated_invoice.currency_id,
                tax_details={
                    **new_tax_details,
                    'taxes_data': list(new_taxes_data_map.values()),
                },
                line_name=f"{orders[0].name}-{orders[-1].name}" if len(orders) > 1 else orders[0].name
            )
            consolidated_base_lines.append(new_base_line)

        vals['base_lines'] = consolidated_base_lines

    def _add_consolidated_invoice_monetary_total_vals(self, vals):
        self._add_document_monetary_total_vals(vals)
        consolidated_invoice = vals["consolidated_invoice"]
        # Add the total amount paid.
        vals.update({
            'total_paid_amount': sum(order.amount_paid / order.currency_rate for order in consolidated_invoice.pos_order_ids),
            'total_paid_amount_currency': sum(consolidated_invoice.pos_order_ids.mapped('amount_paid')),
        })

    def _add_document_tax_grouping_function_vals(self, vals):
        if 'consolidated_invoice' not in vals:
            return super()._add_document_tax_grouping_function_vals(vals)

        def total_grouping_function(_base_line, _tax_data):
            return True

        # Add the grouping functions for the tax totals
        def tax_grouping_function(_base_line, tax_data):
            tax = tax_data and tax_data['tax']
            # Exclude fixed taxes if 'fixed_taxes_as_allowance_charges' is True
            if vals['fixed_taxes_as_allowance_charges'] and tax and tax.amount_type == 'fixed':
                return None

            return {
                'tax_category_code': tax.l10n_my_tax_type if tax else '06',
                'tax_exemption_reason': tax.l10n_my_tax_exemption_reason if tax and tax.l10n_my_tax_type == 'E' else None,
                'amount': tax.amount if tax else 0.0,
                'amount_type': tax.amount_type if tax else 'percent',
            }

        vals['total_grouping_function'] = total_grouping_function
        vals['tax_grouping_function'] = tax_grouping_function

    def _add_consolidated_invoice_header_nodes(self, document_node, vals):
        utc_now = datetime.now(tz=UTC)

        document_node.update({
            'cbc:UBLVersionID': None,
            'cbc:ID': {'_text': vals['document_name']},
            # The issue date and time must be the current time set in the UTC time zone
            'cbc:IssueDate': {'_text': utc_now.strftime("%Y-%m-%d")},
            'cbc:IssueTime': {'_text': utc_now.strftime("%H:%M:%SZ")},
            'cbc:DueDate': None,

            # The current version is 1.1 (document with signature), the type code depends on the move type.
            'cbc:InvoiceTypeCode': {
                '_text': '01',
                'listVersionID': '1.1',
            },
            'cbc:DocumentCurrencyCode': {'_text': vals['currency_id'].name},
            'cac:OrderReference': None,
            'cac:AdditionalDocumentReference': {'cbc:ID': {'_text': vals['export_custom_form_reference']}},
        })

        if vals['currency_id'].name != 'MYR':
            # I couldn't find any information on maximum precision, so we will use the currency format.
            total_amount_in_company_currency = total_amount_in_currency = 0.0
            for base_line in vals['base_lines']:
                total_amount_in_company_currency += base_line['tax_details']['raw_total_included']
                total_amount_in_currency += base_line['tax_details']['raw_total_included_currency']
            rate = self.env.ref('base.MYR').round(abs(total_amount_in_company_currency) / (total_amount_in_currency or 1))
            # Exchange rate information must be provided if applicable
            document_node['cac:TaxExchangeRate'] = {
                'cbc:SourceCurrencyCode': {'_text': vals['currency_id'].name},
                'cbc:TargetCurrencyCode': {'_text': 'MYR'},
                'cbc:CalculationRate': {'_text': rate},
            }

    def _add_consolidated_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        document_node['cac:AccountingSupplierParty'] = {
            'cac:Party': self._get_consolidated_invoice_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'}),
        }

    def _add_consolidated_invoice_accounting_customer_party_nodes(self, document_node, vals):
        document_node['cac:AccountingCustomerParty'] = {
            'cac:Party': self._get_consolidated_invoice_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'}),
        }

    def _get_consolidated_invoice_party_node(self, vals):
        partner = vals["partner"]
        role = vals["role"]
        commercial_partner = partner.commercial_partner_id

        party_identifications = [{
            'cbc:ID': {
                '_text': partner._l10n_my_edi_get_tin_for_myinvois(),
                'schemeID': 'TIN',
            }
        }]
        if partner.l10n_my_identification_type and partner.l10n_my_identification_number:
            party_identifications.append({
                'cbc:ID': {
                    '_text': partner.l10n_my_identification_number,
                    'schemeID': partner.l10n_my_identification_type,
                }
            })
        if partner.sst_registration_number:
            # The supplier can input up to 2 SST numbers, in which case they need to separate both by a ;
            # They can do so in the existing field if they want.
            party_identifications.append({
                "cbc:ID": {
                    "_text": partner.sst_registration_number,
                    "schemeID": "SST",
                }
            })
        if partner.ttx_registration_number:
            party_identifications.append({
                "cbc:ID": {
                    "_text": partner.ttx_registration_number,
                    "schemeID": "TTX",
                }
            })

        return {
            "cac:PartyIdentification": party_identifications,
            "cbc:IndustryClassificationCode": {
                "_text": partner.commercial_partner_id.l10n_my_edi_industrial_classification.code,
                "name": partner.commercial_partner_id.l10n_my_edi_industrial_classification.name,
            } if role == "supplier" else None,
            "cac:PartyName": {
                "cbc:Name": {"_text": partner.display_name},
            },
            "cac:PostalAddress": self._get_address_node(vals),
            "cac:PartyTaxScheme": {
                "cbc:RegistrationName": {"_text": commercial_partner.name},
                "cbc:CompanyID": {"_text": commercial_partner.vat},
                "cac:RegistrationAddress": self._get_address_node(
                    {**vals, "partner": commercial_partner}
                ),
                "cac:TaxScheme": {"cbc:ID": {"_text": "VAT"}},
            },
            "cac:PartyLegalEntity": {
                "cbc:RegistrationName": {"_text": commercial_partner.name},
                "cbc:CompanyID": {"_text": commercial_partner.vat},
                "cac:RegistrationAddress": self._get_address_node(
                    {**vals, "partner": commercial_partner}
                ),
            },
            "cac:Contact": {
                "cbc:ID": {"_text": partner.id},
                "cbc:Name": {"_text": partner.name},
                "cbc:Telephone": {
                    "_text": self._l10n_my_edi_get_formatted_phone_number(partner.phone)
                },
                "cbc:ElectronicMail": {"_text": partner.email},
            },
        }

    def _get_address_node(self, vals):
        """ Generic helper to generate the Address node for a res.partner or res.bank. """
        if 'consolidated_invoice' not in vals:
            return super()._get_address_node(vals)

        partner = vals['partner']
        country_key = 'country' if partner._name == 'res.bank' else 'country_id'
        state_key = 'state' if partner._name == 'res.bank' else 'state_id'
        country = partner[country_key]
        state = partner[state_key]

        subentity_code = partner.state_id.code or ''
        # The API does not expect the country code inside the state code, only the number part.
        if f'{partner.country_id.code}-' in subentity_code:
            subentity_code = subentity_code.split('-')[1]

        return {
            'cac:AddressLine': [
                {'cbc:Line': {'_text': partner.street or None}},
                {'cbc:Line': {'_text': partner.street2 or None}},
            ],
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': state.name},
            'cbc:CountrySubentityCode': {'_text': subentity_code},
            'cac:Country': {
                'cbc:IdentificationCode': {
                    'listID': 'ISO3166-1',
                    'listAgencyID': '6',
                    '_text': COUNTRY_CODE_MAP.get(country.code),
                },
                'cbc:Name': {'_text': country.name},
            },
        }

    def _add_consolidated_invoice_monetary_total_nodes(self, document_node, vals):
        self._add_document_monetary_total_nodes(document_node, vals)
        currency_suffix = vals['currency_suffix']

        amount_paid = vals[f'total_paid_amount{currency_suffix}']
        document_node['cac:PrepaidPayment'] = {
            'cbc:PaidAmount': {
                '_text': self.format_float(amount_paid, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        payable_amount = self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'] - amount_paid, vals['currency_dp'])
        document_node[monetary_total_tag]['cbc:PayableAmount']['_text'] = payable_amount

    def _add_consolidated_invoice_line_nodes(self, document_node, vals):
        self._add_document_line_nodes(document_node, vals)

    def _add_document_line_item_nodes(self, line_node, vals):
        if 'consolidated_invoice' not in vals:
            super()._add_document_line_item_nodes(line_node, vals)
            return

        line_node['cac:Item'] = {
            'cbc:Description': {'_text': vals['base_line']['line_name']},
            'cbc:Name': {'_text': vals['base_line']['line_name']},
            'cac:CommodityClassification': {
                'cbc:ItemClassificationCode': {
                    '_text': '004',
                    'listID': 'CLASS',
                }
            }
        }

    def _add_document_line_amount_nodes(self, line_node, vals):
        super()._add_document_line_amount_nodes(line_node, vals)
        if 'consolidated_invoice' not in vals:
            return

        line_node.update({
            'cac:ItemPriceExtension': {
                'cbc:Amount': {
                    '_text': self.format_float(vals[f"total_excluded{vals['currency_suffix']}"], vals['currency_dp']),
                    'currencyID': vals['currency_name'],
                }
            }
        })

    def _add_document_line_gross_subtotal_and_discount_vals(self, vals):
        """
        As we group lines together, we lose the discount percentage in the process.
        During the grouping, we stored the actual amount in the base line, se we will override here in order to use that
        pre-computed amount.
        """
        super()._add_document_line_gross_subtotal_and_discount_vals(vals)
        if 'consolidated_invoice' not in vals:
            return

        base_line = vals['base_line']

        for currency_suffix in ['', '_currency']:
            discount_amount = base_line[f'discount_amount{currency_suffix}']

            vals[f'discount_amount{currency_suffix}'] = discount_amount
            vals[f'gross_price_unit{currency_suffix}'] += discount_amount  # Price unit should be excluding discounts.

from lxml import etree

from odoo import _, models, Command
from odoo.tools import html2plaintext
from odoo.tools.float_utils import float_is_zero, float_round, float_repr
from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.tools import Invoice, CreditNote, DebitNote


UBL_NAMESPACES = {
    'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


class FloatFmt(float):
    """ A float with a given precision.
    The precision is used when formatting the float.
    """
    def __new__(cls, value, min_dp=2, max_dp=None):
        return super().__new__(cls, value)

    def __init__(self, value, min_dp=2, max_dp=None):
        self.min_dp = min_dp
        self.max_dp = max_dp

    def __str__(self):
        if not isinstance(self.min_dp, int) or (self.max_dp is not None and not isinstance(self.max_dp, int)):
            return "<FloatFmt()>"
        self_float = float(self)
        min_dp_int = int(self.min_dp)
        if self.max_dp is None:
            return float_repr(self_float, min_dp_int)
        else:
            # Format the float to between self.min_dp and self.max_dp decimal places.
            # We start by formatting to self.max_dp, and then remove trailing zeros,
            # but always keep at least self.min_dp decimal places.
            max_dp_int = int(self.max_dp)
            amount_max_dp = float_repr(self_float, max_dp_int)
            num_trailing_zeros = len(amount_max_dp) - len(amount_max_dp.rstrip('0'))
            return float_repr(self_float, max(max_dp_int - num_trailing_zeros, min_dp_int))

    def __repr__(self):
        if not isinstance(self.min_dp, int) or (self.max_dp is not None and not isinstance(self.max_dp, int)):
            return "<FloatFmt()>"
        self_float = float(self)
        min_dp_int = int(self.min_dp)
        if self.max_dp is None:
            return f"FloatFmt({self_float!r}, {min_dp_int!r})"
        else:
            max_dp_int = int(self.max_dp)
            return f"FloatFmt({self_float!r}, {min_dp_int!r}, {max_dp_int!r})"


class AccountEdiXmlUbl_20(models.AbstractModel):
    _name = 'account.edi.xml.ubl_20'
    _inherit = ['account.edi.common']
    _description = "UBL 2.0"

    def _find_value(self, xpath, tree, nsmap=False):
        # EXTENDS account.edi.common
        return super()._find_value(xpath, tree, UBL_NAMESPACES)

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_ubl_20.xml"

    def _get_document_type_code_node(self, invoice, invoice_data):
        """Returns the `DocumentTypeCode` node tag"""
        # To be overriden by custom format if required
        pass

    def _export_invoice(self, invoice):
        """ Generates an UBL 2.0 xml for a given invoice. """
        # 1. Validate the structure of the taxes
        self._validate_taxes(invoice.invoice_line_ids.tax_ids)

        # 2. Instantiate the XML builder
        vals = {'invoice': invoice.with_context(lang=invoice.partner_id.lang)}
        document_node = self._get_invoice_node(vals)

        # 3. Run constraints
        vals['document_node'] = document_node
        errors = [constraint for constraint in self._export_invoice_constraints(invoice, vals).values() if constraint]

        template = self._get_document_template(vals)
        nsmap = self._get_document_nsmap(vals)

        # 4. Render the XML
        xml_content = dict_to_xml(document_node, nsmap=nsmap, template=template)

        # 5. Format the XML
        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8'), set(errors)

    # -------------------------------------------------------------------------
    # EXPORT: Helpers
    # -------------------------------------------------------------------------

    def _get_document_template(self, vals):
        return {
            'invoice': Invoice,
            'credit_note': CreditNote,
            'debit_note': DebitNote,
        }[vals['document_type']]

    def _get_document_nsmap(self, vals):
        return {
            None: {
                'invoice': "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
                'credit_note': "urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2",
                'debit_note': "urn:oasis:names:specification:ubl:schema:xsd:DebitNote-2",
                'order': "urn:oasis:names:specification:ubl:schema:xsd:Order-2",
            }[vals['document_type']],
            'cac': "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            'cbc': "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            'ext': "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2",
        }

    def format_float(self, amount, precision_digits=2):
        return FloatFmt(amount, precision_digits)

    def _get_tags_for_document_type(self, vals):
        return {
            'document_type_code': {
                'invoice': 'cbc:InvoiceTypeCode',
                'credit_note': 'cbc:CreditNoteTypeCode',
                'debit_note': None,
                'order': 'cbc:OrderTypeCode',
            }[vals['document_type']],
            'monetary_total': {
                'invoice': 'cac:LegalMonetaryTotal',
                'credit_note': 'cac:LegalMonetaryTotal',
                'debit_note': 'cac:RequestedMonetaryTotal',
                'order': 'cac:AnticipatedMonetaryTotal',
            }[vals['document_type']],
            'document_line': {
                'invoice': 'cac:InvoiceLine',
                'credit_note': 'cac:CreditNoteLine',
                'debit_note': 'cac:DebitNoteLine',
                'order': 'cac:OrderLine',
            }[vals['document_type']],
            'line_quantity': {
                'invoice': 'cbc:InvoicedQuantity',
                'credit_note': 'cbc:CreditedQuantity',
                'debit_note': 'cbc:DebitedQuantity',
                'order': 'cbc:Quantity',
            }[vals['document_type']]
        }

    def _is_document_allowance_charge(self, base_line):
        """ Whether the base line should be treated as a document-level AllowanceCharge. """
        return base_line['special_type'] == 'early_payment'

    # -------------------------------------------------------------------------
    # EXPORT: account.move specific templates
    # -------------------------------------------------------------------------

    def _get_invoice_node(self, vals):
        self._add_invoice_config_vals(vals)
        self._add_invoice_base_lines_vals(vals)
        self._add_invoice_currency_vals(vals)
        self._add_invoice_tax_grouping_function_vals(vals)
        self._add_invoice_monetary_totals_vals(vals)

        document_node = {}
        self._add_invoice_header_nodes(document_node, vals)
        self._add_invoice_accounting_supplier_party_nodes(document_node, vals)
        self._add_invoice_accounting_customer_party_nodes(document_node, vals)
        self._add_invoice_seller_supplier_party_nodes(document_node, vals)

        if vals['document_type'] == 'invoice':
            self._add_invoice_delivery_nodes(document_node, vals)
            self._add_invoice_payment_means_nodes(document_node, vals)
            self._add_invoice_payment_terms_nodes(document_node, vals)

        self._add_invoice_allowance_charge_nodes(document_node, vals)
        self._add_invoice_exchange_rate_nodes(document_node, vals)
        self._add_invoice_tax_total_nodes(document_node, vals)
        self._add_invoice_monetary_total_nodes(document_node, vals)
        self._add_invoice_line_nodes(document_node, vals)
        return document_node

    def _add_invoice_config_vals(self, vals):
        invoice = vals['invoice']
        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.partner_id
        partner_shipping = invoice.partner_shipping_id or invoice.partner_id

        if invoice.is_purchase_document():
            supplier, customer = customer, supplier
            partner_shipping = customer

        vals.update({
            'document_type': 'debit_note' if 'debit_origin_id' in self.env['account.move']._fields and invoice.debit_origin_id
                else 'credit_note' if invoice.move_type == 'out_refund'
                else 'invoice',

            'process_type': 'billing',
            'supplier': supplier,
            'customer': customer,
            'partner_shipping': partner_shipping,

            'currency_id': invoice.currency_id,
            'company_currency_id': invoice.company_id.currency_id,

            'use_company_currency': False,  # If true, use the company currency for the amounts instead of the invoice currency
            'fixed_taxes_as_allowance_charges': True,  # If true, include fixed taxes as AllowanceCharges on lines instead of as taxes
        })

    def _add_invoice_base_lines_vals(self, vals):
        invoice = vals['invoice']
        base_lines, _tax_lines = invoice._get_rounded_base_and_tax_lines()
        vals['base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] != 'cash_rounding']
        vals['cash_rounding_base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] == 'cash_rounding']

    def _add_invoice_currency_vals(self, vals):
        self._add_document_currency_vals(vals)

    def _add_invoice_tax_grouping_function_vals(self, vals):
        self._add_document_tax_grouping_function_vals(vals)

    def _add_invoice_monetary_totals_vals(self, vals):
        self._add_document_monetary_total_vals(vals)

    def _add_invoice_header_nodes(self, document_node, vals):
        invoice = vals['invoice']
        document_node.update({
            'cbc:UBLVersionID': {'_text': '2.0'},
            'cbc:ID': {'_text': invoice.name},
            'cbc:IssueDate': {'_text': invoice.invoice_date},
            'cbc:InvoiceTypeCode': {'_text': 389 if vals['process_type'] == 'selfbilling' else 380} if vals['document_type'] == 'invoice' else None,
            'cbc:Note': {'_text': html2plaintext(invoice.narration)} if invoice.narration else None,
            'cbc:DocumentCurrencyCode': {'_text': invoice.currency_id.name},
            'cac:OrderReference': {
                # OrderReference/ID (order_reference) is mandatory inside the OrderReference node
                'cbc:ID': {'_text': invoice.ref or invoice.name},
                # OrderReference/SalesOrderID (sales_order_id) is optional
                'cbc:SalesOrderID': {
                    '_text': ",".join(invoice.invoice_line_ids.sale_line_ids.order_id.mapped('name'))
                } if 'sale_line_ids' in invoice.invoice_line_ids._fields else None,
            }
        })

    def _add_invoice_accounting_supplier_party_nodes(self, document_node, vals):
        document_node['cac:AccountingSupplierParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['supplier'], 'role': 'supplier'}),
        }

    def _add_invoice_accounting_customer_party_nodes(self, document_node, vals):
        document_node['cac:AccountingCustomerParty'] = {
            'cac:Party': self._get_party_node({**vals, 'partner': vals['customer'], 'role': 'customer'}),
        }

    def _add_invoice_seller_supplier_party_nodes(self, document_node, vals):
        pass

    def _add_invoice_delivery_nodes(self, document_node, vals):
        invoice = vals['invoice']
        document_node['cac:Delivery'] = {
            'cbc:ActualDeliveryDate': {'_text': invoice.delivery_date},
            'cac:DeliveryLocation': {
                'cac:Address': self._get_address_node({'partner': vals['partner_shipping']})
            },
        }

    def _add_invoice_payment_means_nodes(self, document_node, vals):
        invoice = vals['invoice']
        if invoice.move_type == 'out_invoice':
            if invoice.partner_bank_id:
                payment_means_code, payment_means_name = 30, 'credit transfer'
            else:
                payment_means_code, payment_means_name = 'ZZZ', 'mutually defined'
        else:
            payment_means_code, payment_means_name = 57, 'standing agreement'

        # in Denmark payment code 30 is not allowed. we hardcode it to 1 ("unknown") for now
        # as we cannot deduce this information from the invoice
        if invoice.partner_id.country_code == 'DK':
            payment_means_code, payment_means_name = 1, 'unknown'

        document_node['cac:PaymentMeans'] = {
            'cbc:PaymentMeansCode': {
                '_text': payment_means_code,
                'name': payment_means_name,
            },
            'cbc:PaymentDueDate': {'_text': invoice.invoice_date_due or invoice.invoice_date},
            'cbc:InstructionID': {'_text': invoice.payment_reference},
            'cbc:PaymentID': {'_text': invoice.payment_reference or invoice.name},
            'cac:PayeeFinancialAccount': self._get_financial_account_node({
                **vals, 'partner_bank': invoice.partner_bank_id
            }) if invoice.partner_bank_id else None
        }

    def _add_invoice_payment_terms_nodes(self, document_node, vals):
        invoice = vals['invoice']
        payment_term = invoice.invoice_payment_term_id
        if payment_term:
            document_node['cac:PaymentTerms'] = {
                # The payment term's note is automatically embedded in a <p> tag in Odoo
                'cbc:Note': {'_text': html2plaintext(payment_term.note)}
            }

    def _add_invoice_allowance_charge_nodes(self, document_node, vals):
        self._add_document_allowance_charge_nodes(document_node, vals)

    def _add_invoice_exchange_rate_nodes(self, document_node, vals):
        pass

    def _add_invoice_tax_total_nodes(self, document_node, vals):
        self._add_document_tax_total_nodes(document_node, vals)

    def _add_invoice_monetary_total_nodes(self, document_node, vals):
        self._add_document_monetary_total_nodes(document_node, vals)
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        invoice = vals['invoice']
        document_node[monetary_total_tag].update({
            'cbc:PrepaidAmount': {
                '_text': self.format_float(invoice.amount_total - invoice.amount_residual, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PayableRoundingAmount': {
                '_text': self.format_float(vals['cash_rounding_base_amount_currency'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals['cash_rounding_base_amount_currency'] else None,
            'cbc:PayableAmount': {
                '_text': self.format_float(invoice.amount_residual, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        })

    def _get_invoice_line_node(self, vals):
        self._add_invoice_line_vals(vals)

        line_node = {}
        self._add_invoice_line_id_nodes(line_node, vals)
        self._add_invoice_line_note_nodes(line_node, vals)
        self._add_invoice_line_amount_nodes(line_node, vals)
        self._add_invoice_line_period_nodes(line_node, vals)
        self._add_invoice_line_allowance_charge_nodes(line_node, vals)
        self._add_invoice_line_tax_total_nodes(line_node, vals)
        self._add_invoice_line_item_nodes(line_node, vals)
        self._add_invoice_line_tax_category_nodes(line_node, vals)
        self._add_invoice_line_price_nodes(line_node, vals)
        self._add_invoice_line_pricing_reference_nodes(line_node, vals)
        return line_node

    def _add_invoice_line_nodes(self, document_node, vals):
        line_idx = 1

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[line_tag] = line_nodes = []
        for base_line in vals['base_lines']:
            # Only use product lines to generate the UBL InvoiceLines.
            # Other lines should be represented as AllowanceCharges.
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                line_node = self._get_invoice_line_node(line_vals)
                line_nodes.append(line_node)
                line_idx += 1

    def _add_invoice_line_vals(self, vals):
        self._add_document_line_vals(vals)

    def _add_invoice_line_id_nodes(self, line_node, vals):
        self._add_document_line_id_nodes(line_node, vals)

    def _add_invoice_line_note_nodes(self, line_node, vals):
        self._add_document_line_note_nodes(line_node, vals)

    def _add_invoice_line_amount_nodes(self, line_node, vals):
        self._add_document_line_amount_nodes(line_node, vals)

    def _add_invoice_line_period_nodes(self, line_node, vals):
        pass

    def _add_invoice_line_allowance_charge_nodes(self, line_node, vals):
        self._add_document_line_allowance_charge_nodes(line_node, vals)

    def _add_invoice_line_tax_total_nodes(self, line_node, vals):
        self._add_document_line_tax_total_nodes(line_node, vals)

    def _add_invoice_line_item_nodes(self, line_node, vals):
        self._add_document_line_item_nodes(line_node, vals)

        line = vals['base_line']['record']
        if line_name := line.name and line.name.replace('\n', ' '):
            line_node['cac:Item']['cbc:Description']['_text'] = line_name
            if not line_node['cac:Item']['cbc:Name']['_text']:
                line_node['cac:Item']['cbc:Name']['_text'] = line_name

    def _add_invoice_line_tax_category_nodes(self, line_node, vals):
        self._add_document_line_tax_category_nodes(line_node, vals)

    def _add_invoice_line_price_nodes(self, line_node, vals):
        self._add_document_line_price_nodes(line_node, vals)

    def _add_invoice_line_pricing_reference_nodes(self, line_node, vals):
        pass

    # -------------------------------------------------------------------------
    # EXPORT: Generic templates
    # -------------------------------------------------------------------------

    def _add_document_currency_vals(self, vals):
        """ Add the 'currency_suffix', 'currency_dp' and 'currency_name'. """
        vals['currency_suffix'] = '' if vals['use_company_currency'] else '_currency'

        currency = vals['company_currency_id'] if vals['use_company_currency'] else vals['currency_id']
        vals['currency_dp'] = self._get_currency_decimal_places(currency)
        vals['currency_name'] = currency.name

    def _add_document_tax_grouping_function_vals(self, vals):
        # Add the grouping functions for the monetary totals and tax totals
        customer = vals['customer']
        supplier = vals['supplier']

        # This function will be used when computing the monetary totals on the document level.
        # It should return True for all taxes which should be included in the total.
        def total_grouping_function(base_line, tax_data):
            return True

        # This function will be used when computing the tax totals on the document and line level.
        # It should group taxes together according to the tax catagory with which they will be reported.
        # Any taxes that should be included in the tax totals should be included.
        def tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            # Exclude fixed taxes if 'fixed_taxes_as_allowance_charges' is True
            if vals['fixed_taxes_as_allowance_charges'] and tax and tax.amount_type == 'fixed':
                return None
            return {
                'tax_category_code': self._get_tax_category_code(customer.commercial_partner_id, supplier, tax),
                **self._get_tax_exemption_reason(customer.commercial_partner_id, supplier, tax),
                # Reverse-charge taxes with +100/-100% repartition lines are used in vendor bills.
                # In a self-billed invoice, we report them from the seller's perspective, so
                # we change their percentage to 0%.
                'amount': tax.amount if tax and not tax.has_negative_factor else 0.0,
                'amount_type': tax.amount_type if tax else 'percent',
            }

        vals['total_grouping_function'] = total_grouping_function
        vals['tax_grouping_function'] = tax_grouping_function

    def _add_document_monetary_total_vals(self, vals):
        # Compute the monetary totals for the document
        def fixed_total_grouping_function(base_line, tax_data):
            if vals['fixed_taxes_as_allowance_charges'] and tax_data and tax_data['tax'].amount_type == 'fixed':
                return vals['total_grouping_function'](base_line, tax_data)

        for currency_suffix in ['', '_currency']:
            for key in ['total_allowance', 'total_charge', 'total_lines']:
                vals[f'{key}{currency_suffix}'] = 0.0

        for base_line in vals['base_lines']:
            aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, fixed_total_grouping_function)

            for currency_suffix in ['', '_currency']:
                base_line_total_excluded = \
                    base_line['tax_details'][f'total_excluded{currency_suffix}'] \
                    + base_line['tax_details'][f'delta_total_excluded{currency_suffix}'] \
                    + sum(
                        tax_details[f'tax_amount{currency_suffix}']
                        for grouping_key, tax_details in aggregated_tax_details.items()
                        if grouping_key
                    )

                if self._is_document_allowance_charge(base_line):
                    if base_line_total_excluded < 0.0:
                        vals[f'total_allowance{currency_suffix}'] += -base_line_total_excluded
                    else:
                        vals[f'total_charge{currency_suffix}'] += base_line_total_excluded
                else:
                    vals[f'total_lines{currency_suffix}'] += base_line_total_excluded

        for currency_suffix in ['', '_currency']:
            vals[f'tax_exclusive_amount{currency_suffix}'] = vals[f'total_lines{currency_suffix}'] \
                + vals[f'total_charge{currency_suffix}'] \
                - vals[f'total_allowance{currency_suffix}']

        def non_fixed_total_grouping_function(base_line, tax_data):
            if vals['fixed_taxes_as_allowance_charges'] and tax_data and tax_data['tax'].amount_type == 'fixed':
                return None
            return vals['total_grouping_function'](base_line, tax_data)

        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], non_fixed_total_grouping_function)
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        for currency_suffix in ['', '_currency']:
            vals[f'tax_inclusive_amount{currency_suffix}'] = vals[f'tax_exclusive_amount{currency_suffix}'] \
                + sum(
                    tax_details[f'tax_amount{currency_suffix}']
                    for grouping_key, tax_details in aggregated_tax_details.items()
                    if grouping_key
                )

        # Cash rounding for 'add_invoice_line' cash rounding strategy
        # (For the 'biggest_tax' strategy the amounts are directly included in the tax amounts.)
        for currency_suffix in ['', '_currency']:
            vals[f'cash_rounding_base_amount{currency_suffix}'] = 0.0
            for base_line in vals.setdefault('cash_rounding_base_lines', []):
                tax_details = base_line['tax_details']
                vals[f'cash_rounding_base_amount{currency_suffix}'] += tax_details[f'total_excluded{currency_suffix}']

    # -------------------------------------------------------------------------
    # EXPORT: Generic templates - partner-related nodes
    # -------------------------------------------------------------------------

    def _get_address_node(self, vals):
        """ Generic helper to generate the Address node for a res.partner or res.bank. """
        partner = vals['partner']
        country_key = 'country' if partner._name == 'res.bank' else 'country_id'
        state_key = 'state' if partner._name == 'res.bank' else 'state_id'
        country = partner[country_key]
        state = partner[state_key]

        return {
            'cbc:StreetName': {'_text': partner.street},
            'cbc:AdditionalStreetName': {'_text': partner.street2},
            'cbc:CityName': {'_text': partner.city},
            'cbc:PostalZone': {'_text': partner.zip},
            'cbc:CountrySubentity': {'_text': state.name},
            'cbc:CountrySubentityCode': {'_text': state.code},
            'cac:Country': {
                'cbc:IdentificationCode': {'_text': country.code},
                'cbc:Name': {'_text': country.name},
            },
        }

    def _get_party_node(self, vals):
        """ Generic helper to generate the Party node for a res.partner. """
        partner = vals['partner']
        commercial_partner = partner.commercial_partner_id
        return {
            'cac:PartyIdentification': {
                'cbc:ID': {'_text': commercial_partner.ref},
            },
            'cac:PartyName': {
                'cbc:Name': {'_text': partner.display_name if partner.name else commercial_partner.display_name},
            },
            'cac:PostalAddress': self._get_address_node(vals),
            'cac:PartyTaxScheme': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:RegistrationAddress': self._get_address_node({**vals, 'partner': commercial_partner}),
                'cac:TaxScheme': {
                    'cbc:ID': {
                        '_text': ('NOT_EU_VAT' if commercial_partner.country_id and
                                commercial_partner.vat and
                                not commercial_partner.vat[:2].isalpha() else 'VAT')
                    }
                },
            },
            'cac:PartyLegalEntity': {
                'cbc:RegistrationName': {'_text': commercial_partner.name},
                'cbc:CompanyID': {'_text': commercial_partner.vat},
                'cac:RegistrationAddress': self._get_address_node({**vals, 'partner': commercial_partner}),
            },
            'cac:Contact': {
                'cbc:ID': {'_text': partner.id},
                'cbc:Name': {'_text': partner.name},
                'cbc:Telephone': {'_text': partner.phone},
                'cbc:ElectronicMail': {'_text': partner.email},
            },
        }

    def _get_financial_account_node(self, vals):
        """ Generic helper to generate the FinancialAccount node for a res.partner.bank """
        partner_bank = vals['partner_bank']
        bank = partner_bank.bank_id
        financial_institution_branch = None
        if bank:
            financial_institution_branch = {
                'cbc:ID': {
                    '_text': bank.bic,
                    'schemeID': 'BIC'
                },
                'cac:FinancialInstitution': {
                    'cbc:ID': {
                        '_text': bank.bic,
                        'schemeID': 'BIC'
                    },
                    'cbc:Name': {'_text': bank.name},
                    'cac:Address': self._get_address_node({**vals, 'partner': bank})
                }
            }
        return {
            'cbc:ID': {'_text': partner_bank.acc_number.replace(' ', '')},
            'cac:FinancialInstitutionBranch': financial_institution_branch
        }

    # -------------------------------------------------------------------------
    # EXPORT: Generic templates for tax-related nodes
    # -------------------------------------------------------------------------

    def _add_document_tax_total_nodes(self, document_node, vals):
        """ Generic helper to fill the TaxTotal and WithholdingTaxTotal nodes for a document. """
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], vals['tax_grouping_function'])
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        document_node['cac:TaxTotal'] = self._get_tax_total_node({**vals, 'aggregated_tax_details': aggregated_tax_details, 'role': 'document'})
        document_node['cac:WithholdingTaxTotal'] = None

    def _add_tax_total_node_in_company_currency(self, document_node, vals):
        """ Generic helper to add a TaxTotal section in the company currency. """
        company_currency = vals['invoice'].company_id.currency_id
        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], vals['tax_grouping_function'])
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        tax_total_node_in_company_currency = self._get_tax_total_node({
            **vals,
            'aggregated_tax_details': aggregated_tax_details,
            'currency_suffix': '',
            'currency_dp': self._get_currency_decimal_places(company_currency),
            'currency_name': company_currency.name,
            'role': 'document'
        })
        document_node['cac:TaxTotal'].append(tax_total_node_in_company_currency)

    def _get_tax_total_node(self, vals):
        """ Generic helper to generate a TaxTotal node given a dict of aggregated tax details. """
        aggregated_tax_details = vals['aggregated_tax_details']
        currency_suffix = vals['currency_suffix']
        sign = vals.get('sign', 1)
        total_tax_amount = sum(
            values[f'tax_amount{currency_suffix}']
            for grouping_key, values in aggregated_tax_details.items()
            if grouping_key
        )
        return {
            'cbc:TaxAmount': {
                '_text': self.format_float(sign * total_tax_amount, vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cac:TaxSubtotal': [
                self._get_tax_subtotal_node({
                    **vals,
                    'tax_details': tax_details,
                    'grouping_key': grouping_key,
                })
                for grouping_key, tax_details in aggregated_tax_details.items()
                if grouping_key
            ]
        }

    def _get_tax_subtotal_node(self, vals):
        """ Generic helper to generate a TaxSubtotal node given a tax grouping key dict and associated tax values. """
        tax_details = vals['tax_details']
        grouping_key = vals['grouping_key']
        sign = vals.get('sign', 1)
        currency_suffix = vals['currency_suffix']
        return {
            'cbc:TaxableAmount': {
                '_text': self.format_float(tax_details[f'base_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:TaxAmount': {
                '_text': self.format_float(sign * tax_details[f'tax_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
            'cac:TaxCategory': self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
        }

    def _get_tax_category_node(self, vals):
        """ Generic helper to generate a TaxCategory node given a tax grouping key dict. """
        grouping_key = vals['grouping_key']
        return {
            'cbc:ID': {'_text': grouping_key['tax_category_code']},
            'cbc:Name': {'_text': grouping_key.get('name')},
            'cbc:Percent': {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
            'cbc:TaxExemptionReasonCode': {'_text': grouping_key.get('tax_exemption_reason_code')},
            'cbc:TaxExemptionReason': {'_text': grouping_key.get('tax_exemption_reason')},
            'cac:TaxScheme': {
                'cbc:ID': {'_text': 'VAT'},
            }
        }

    def _add_document_monetary_total_nodes(self, document_node, vals):
        """ Generic helper to fill the MonetaryTotal node for a document given a list of base_lines. """
        monetary_total_tag = self._get_tags_for_document_type(vals)['monetary_total']
        currency_suffix = vals['currency_suffix']

        document_node[monetary_total_tag] = {
            'cbc:LineExtensionAmount': {
                '_text': self.format_float(vals[f'total_lines{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxExclusiveAmount': {
                '_text': self.format_float(vals[f'tax_exclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:TaxInclusiveAmount': {
                '_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:AllowanceTotalAmount': {
                '_text': self.format_float(vals[f'total_allowance{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals[f'total_allowance{currency_suffix}'] else None,
            'cbc:ChargeTotalAmount': {
                '_text': self.format_float(vals[f'total_charge{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals[f'total_charge{currency_suffix}'] else None,
            'cbc:PrepaidAmount': {
                '_text': self.format_float(0.0, vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
            'cbc:PayableRoundingAmount': {
                '_text': self.format_float(vals[f'cash_rounding_base_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            } if vals[f'cash_rounding_base_amount{currency_suffix}'] else None,
            'cbc:PayableAmount': {
                '_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        }

    def _get_document_line_node(self, vals):
        self._add_document_line_vals(vals)

        line_node = {}
        self._add_document_line_id_nodes(line_node, vals)
        self._add_document_line_note_nodes(line_node, vals)
        self._add_document_line_amount_nodes(line_node, vals)
        self._add_document_line_period_nodes(line_node, vals)
        self._add_document_line_allowance_charge_nodes(line_node, vals)
        self._add_document_line_tax_total_nodes(line_node, vals)
        self._add_document_line_item_nodes(line_node, vals)
        self._add_document_line_tax_category_nodes(line_node, vals)
        self._add_document_line_price_nodes(line_node, vals)
        self._add_document_line_pricing_reference_nodes(line_node, vals)
        return line_node

    def _add_document_line_nodes(self, document_node, vals):
        line_idx = 1

        line_tag = self._get_tags_for_document_type(vals)['document_line']
        document_node[line_tag] = line_nodes = []
        for base_line in vals['base_lines']:
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                line_node = self._get_document_line_node(line_vals)
                line_nodes.append(line_node)
                line_idx += 1

    # -------------------------------------------------------------------------
    # EXPORT: Templates for document-level allowance charge nodes
    # -------------------------------------------------------------------------

    def _add_document_allowance_charge_nodes(self, document_node, vals):
        """ Generic helper to fill the AllowanceCharge nodes for a document given a list of base_lines. """
        # AllowanceCharge doesn't exist in debit notes in UBL 2.0
        if vals['document_type'] != 'debit_note':
            document_node['cac:AllowanceCharge'] = []
            for base_line in vals['base_lines']:
                if self._is_document_allowance_charge(base_line):
                    document_node['cac:AllowanceCharge'].append(
                        self._get_document_allowance_charge_node({**vals, 'base_line': base_line})
                    )

    def _get_document_allowance_charge_node(self, vals):
        """ Generic helper to generate a document-level AllowanceCharge node given a base_line. """
        base_line = vals['base_line']
        currency_suffix = vals['currency_suffix']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])
        base_amount = base_line['tax_details'][f'total_excluded{currency_suffix}']
        return {
            'cbc:ChargeIndicator': {'_text': 'false' if base_amount < 0.0 else 'true'},
            'cbc:AllowanceChargeReasonCode': {'_text': '66' if base_amount < 0.0 else 'ZZZ'},
            'cbc:AllowanceChargeReason': {'_text': _("Conditional cash/payment discount")},
            'cbc:Amount': {
                '_text': self.format_float(abs(base_amount), vals['currency_dp']),
                'currencyID': vals['currency_name']
            },
            'cac:TaxCategory': [
                self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
                for grouping_key in aggregated_tax_details
                if grouping_key
            ]
        }

    # -------------------------------------------------------------------------
    # EXPORT: Templates for line nodes
    # -------------------------------------------------------------------------

    def _add_document_line_vals(self, vals):
        """ Generic helper to calculate the amounts for a document line. """
        self._add_document_line_total_vals(vals)
        self._add_document_line_gross_subtotal_and_discount_vals(vals)

    def _add_document_line_total_vals(self, vals):
        base_line = vals['base_line']

        def fixed_total_grouping_function(base_line, tax_data):
            if vals['fixed_taxes_as_allowance_charges'] and tax_data and tax_data['tax'].amount_type == 'fixed':
                return vals['total_grouping_function'](base_line, tax_data)

        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, fixed_total_grouping_function)

        for currency_suffix in ['', '_currency']:
            vals[f'total_fixed_taxes{currency_suffix}'] = sum(
                tax_details[f'tax_amount{currency_suffix}']
                for grouping_key, tax_details in aggregated_tax_details.items()
                if grouping_key
            )

            vals[f'total_excluded{currency_suffix}'] = \
                base_line['tax_details'][f'total_excluded{currency_suffix}'] \
                + base_line['tax_details'][f'delta_total_excluded{currency_suffix}'] \
                + vals[f'total_fixed_taxes{currency_suffix}']

    def _add_document_line_gross_subtotal_and_discount_vals(self, vals):
        base_line = vals['base_line']
        company_currency = vals['company_currency_id']

        discount_factor = 1 - (base_line['discount'] / 100.0)

        if discount_factor != 0.0:
            gross_subtotal_currency = base_line['currency_id'].round(base_line['tax_details']['raw_total_excluded_currency'] / discount_factor)
            gross_subtotal = company_currency.round(base_line['tax_details']['raw_total_excluded'] / discount_factor)
        else:
            gross_subtotal_currency = base_line['currency_id'].round(base_line['price_unit'] * base_line['quantity'])
            gross_subtotal = company_currency.round(gross_subtotal_currency / base_line['rate'])

        if base_line['quantity'] == 0.0 or discount_factor == 0.0:
            gross_price_unit_currency = base_line['price_unit']
            gross_price_unit = company_currency.round(base_line['price_unit'] / base_line['rate'])
        else:
            gross_price_unit_currency = gross_subtotal_currency / base_line['quantity']
            gross_price_unit = gross_subtotal / base_line['quantity']

        discount_amount_currency = gross_subtotal_currency - base_line['tax_details']['total_excluded_currency']
        discount_amount = gross_subtotal - base_line['tax_details']['total_excluded']

        vals.update({
            'discount_amount_currency': discount_amount_currency,
            'discount_amount': discount_amount,
            'gross_subtotal_currency': gross_subtotal_currency,
            'gross_subtotal': gross_subtotal,
            'gross_price_unit_currency': gross_price_unit_currency,
            'gross_price_unit': gross_price_unit,
        })

    def _add_document_line_id_nodes(self, line_node, vals):
        line_node['cbc:ID'] = {'_text': vals['line_idx']}

    def _add_document_line_note_nodes(self, line_node, vals):
        pass

    def _add_document_line_amount_nodes(self, line_node, vals):
        currency_suffix = vals['currency_suffix']
        base_line = vals['base_line']

        quantity_tag = self._get_tags_for_document_type(vals)['line_quantity']

        line_node.update({
            quantity_tag: {
                '_text': base_line['quantity'],
                'unitCode': self._get_uom_unece_code(base_line['product_uom_id']),
            },
            'cbc:LineExtensionAmount': {
                '_text': self.format_float(vals[f'total_excluded{currency_suffix}'], vals['currency_dp']),
                'currencyID': vals['currency_name'],
            },
        })

    def _add_document_line_period_nodes(self, line_node, vals):
        pass

    def _add_document_line_item_nodes(self, line_node, vals):
        product = vals['base_line']['product_id']

        line_node['cac:Item'] = {
            'cbc:Description': {'_text': product.description_sale},
            'cbc:Name': {'_text': product.name},
            'cac:SellersItemIdentification': {
                'cbc:ID': {'_text': product.default_code},
            },
            'cac:StandardItemIdentification': {
                'cbc:ID': {
                    '_text': product.barcode,
                    'schemeID': '0160',  # GTIN
                } if product.barcode else None,
            },
            'cac:AdditionalItemProperty': [
                {
                    'cbc:Name': {'_text': value.attribute_id.name},
                    'cbc:Value': {'_text': value.name},
                } for value in product.product_template_attribute_value_ids
            ],
        }

    def _add_document_line_allowance_charge_nodes(self, line_node, vals):
        if vals['document_type'] not in {'credit_note', 'debit_note'}:
            line_node['cac:AllowanceCharge'] = []
            if node := self._get_line_discount_allowance_charge_node(vals):
                line_node['cac:AllowanceCharge'].append(node)
            if vals['fixed_taxes_as_allowance_charges']:
                line_node['cac:AllowanceCharge'].extend(self._get_line_fixed_tax_allowance_charge_nodes(vals))

    def _get_line_discount_allowance_charge_node(self, vals):
        currency_suffix = vals['currency_suffix']
        if float_is_zero(vals[f'discount_amount{currency_suffix}'], precision_digits=vals['currency_dp']):
            return None

        return {
            'cbc:ChargeIndicator': {'_text': 'false' if vals[f'discount_amount{currency_suffix}'] > 0 else 'true'},
            'cbc:AllowanceChargeReasonCode': {'_text': '95'},
            'cbc:Amount': {
                '_text': self.format_float(
                    abs(vals[f'discount_amount{currency_suffix}']),
                    vals['currency_dp'],
                ),
                'currencyID': vals['currency_name'],
            },
        }

    def _get_line_fixed_tax_allowance_charge_nodes(self, vals):
        fixed_tax_aggregated_tax_details = self._get_line_fixed_tax_aggregated_tax_details(vals)
        currency_suffix = vals['currency_suffix']

        allowance_charge_nodes = []
        for grouping_key, tax_details in fixed_tax_aggregated_tax_details.items():
            if grouping_key:
                allowance_charge_nodes.append({
                    'cbc:ChargeIndicator': {'_text': 'true' if tax_details[f'tax_amount{currency_suffix}'] > 0 else 'false'},
                    'cbc:AllowanceChargeReasonCode': {'_text': 'AEO'},
                    'cbc:AllowanceChargeReason': {'_text': grouping_key},
                    'cbc:Amount': {
                        '_text': self.format_float(
                            abs(tax_details[f'tax_amount{currency_suffix}']),
                            vals['currency_dp'],
                        ),
                        'currencyID': vals['currency_name'],
                    },
                })
        return allowance_charge_nodes

    def _get_line_fixed_tax_aggregated_tax_details(self, vals):
        base_line = vals['base_line']

        def fixed_tax_grouping_function(base_line, tax_data):
            tax = tax_data and tax_data['tax']
            if not tax or tax.amount_type != 'fixed':
                return None
            return tax.name

        return self.env['account.tax']._aggregate_base_line_tax_details(base_line, fixed_tax_grouping_function)

    def _add_document_line_tax_category_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])
        line_node.setdefault('cac:Item', {})['cac:ClassifiedTaxCategory'] = [
            self._get_tax_category_node({**vals, 'grouping_key': grouping_key})
            for grouping_key in aggregated_tax_details
            if grouping_key
        ]

    def _add_document_line_tax_total_nodes(self, line_node, vals):
        base_line = vals['base_line']
        aggregated_tax_details = self.env['account.tax']._aggregate_base_line_tax_details(base_line, vals['tax_grouping_function'])
        line_node['cac:TaxTotal'] = self._get_tax_total_node({**vals, 'aggregated_tax_details': aggregated_tax_details, 'role': 'line'})

    def _add_document_line_price_nodes(self, line_node, vals):
        currency_suffix = vals['currency_suffix']
        product_price_dp = self.env['decimal.precision'].precision_get('Product Price')

        line_node['cac:Price'] = {
            'cbc:PriceAmount': {
                '_text': float_round(
                    vals[f'gross_price_unit{currency_suffix}'],
                    precision_digits=product_price_dp,
                ),
                'currencyID': vals['currency_name'],
            },
        }

    def _add_document_line_pricing_reference_nodes(self, line_node, vals):
        pass

    # -------------------------------------------------------------------------
    # EXPORT: Constraints
    # -------------------------------------------------------------------------

    def _export_invoice_constraints(self, invoice, vals):
        constraints = self._invoice_constraints_common(invoice)
        constraints.update({
            'ubl20_supplier_name_required': self._check_required_fields(vals['supplier'], 'name'),
            'ubl20_customer_name_required': self._check_required_fields(vals['customer'].commercial_partner_id, 'name'),
            'ubl20_invoice_name_required': self._check_required_fields(invoice, 'name'),
            'ubl20_invoice_date_required': self._check_required_fields(invoice, 'invoice_date'),
        })
        return constraints

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_retrieve_partner_vals(self, tree, role):
        """ Returns a dict of values that will be used to retrieve the partner """
        return {
            'vat': self._find_value(f'.//cac:{role}Party//cbc:CompanyID[string-length(text()) > 5]', tree),
            'phone': self._find_value(f'.//cac:{role}Party//cac:Contact//cbc:Telephone', tree),
            'email': self._find_value(f'.//cac:{role}Party//cac:Contact//cbc:ElectronicMail', tree),
            'name': self._find_value(f'.//cac:{role}Party//cac:Contact//cbc:Name', tree) or
                    self._find_value(f'.//cac:{role}Party//cbc:RegistrationName', tree),
            'postal_address': self._get_postal_address(tree, role),
        }

    def _get_postal_address(self, tree, role):
        return {
            'country_code': self._find_value(f'.//cac:{role}Party//cac:PostalAddress/cac:Country/cbc:IdentificationCode', tree),
            'street': self._find_value(f'.//cac:{role}Party//cac:PostalAddress/cbc:StreetName', tree),
            'additional_street': self._find_value(f'.//cac:{role}Party//cac:PostalAddress/cbc:AdditionalStreetName', tree),
            'city': self._find_value(f'.//cac:{role}Party//cac:PostalAddress/cbc:CityName', tree),
            'zip': self._find_value(f'.//cac:{role}Party//cac:PostalAddress/cbc:PostalZone', tree),
            'state_code': self._find_value(f'.//cac:{role}Party//cac:PostalAddress/cbc:CountrySubentityCode', tree),
        }

    def _import_fill_invoice(self, invoice, tree, qty_factor):
        logs = []
        invoice_values = {}
        if qty_factor == -1:
            logs.append(_("The invoice has been converted into a credit note and the quantities have been reverted."))
        role = "AccountingCustomer" if invoice.journal_id.type == 'sale' else "AccountingSupplier"
        partner, partner_logs = self._import_partner(invoice.company_id, **self._import_retrieve_partner_vals(tree, role))
        # Need to set partner before to compute bank and lines properly
        invoice.partner_id = partner.id
        invoice_values['currency_id'], currency_logs = self._import_currency(tree, './/{*}DocumentCurrencyCode')
        invoice_values['invoice_date'] = tree.findtext('./{*}IssueDate')
        invoice_values['invoice_date_due'] = self._find_value(('./cbc:DueDate', './/cbc:PaymentDueDate'), tree)
        # ==== partner_bank_id ====
        bank_detail_nodes = tree.findall('.//{*}PaymentMeans')
        bank_details = [bank_detail_node.findtext('{*}PayeeFinancialAccount/{*}ID') for bank_detail_node in bank_detail_nodes]
        if bank_details:
            self._import_partner_bank(invoice, bank_details)

        # ==== ref, invoice_origin, narration, payment_reference ====
        ref = tree.findtext('./{*}ID')
        if ref and invoice.is_sale_document(include_receipts=True) and invoice.quick_edit_mode:
            invoice_values['name'] = ref
        elif ref:
            invoice_values['ref'] = ref
        invoice_values['invoice_origin'] = (
            tree.findtext('./{*}OrderReference/{*}ID')
            or ' '.join([desc.text for desc in tree.findall('.//{*}Item/{*}Description')])
            or None
        )
        invoice_values['narration'] = self._import_description(tree, xpaths=['./{*}Note', './{*}PaymentTerms/{*}Note'])
        invoice_values['payment_reference'] = tree.findtext('./{*}PaymentMeans/{*}PaymentID')

        # ==== Delivery ====
        delivery_date = tree.find('.//{*}Delivery/{*}ActualDeliveryDate')
        invoice.delivery_date = delivery_date is not None and delivery_date.text

        # ==== invoice_incoterm_id ====
        incoterm_code = tree.findtext('./{*}TransportExecutionTerms/{*}DeliveryTerms/{*}ID')
        if incoterm_code:
            incoterm = self.env['account.incoterms'].search([('code', '=', incoterm_code)], limit=1)
            if incoterm:
                invoice_values['invoice_incoterm_id'] = incoterm.id

        # ==== Document level AllowanceCharge, Prepaid Amounts, Invoice Lines, Payable Rounding Amount ====
        allowance_charges_line_vals, allowance_charges_logs = self._import_document_allowance_charges(tree, invoice, invoice.journal_id.type, qty_factor)
        logs += self._import_prepaid_amount(invoice, tree, './{*}LegalMonetaryTotal/{*}PrepaidAmount', qty_factor)
        line_tag = (
            'InvoiceLine'
            if invoice.move_type in ('in_invoice', 'out_invoice') or qty_factor == -1
            else 'CreditNoteLine'
        )
        invoice_line_vals, line_logs = self._import_lines(invoice, tree, './{*}' + line_tag, document_type=invoice.move_type, tax_type=invoice.journal_id.type, qty_factor=qty_factor)
        rounding_line_vals, rounding_logs = self._import_rounding_amount(invoice, tree, './{*}LegalMonetaryTotal/{*}PayableRoundingAmount', document_type=invoice.move_type, qty_factor=qty_factor)
        line_vals = allowance_charges_line_vals + invoice_line_vals + rounding_line_vals

        invoice_values = {
            **invoice_values,
            'invoice_line_ids': [Command.create(line_value) for line_value in line_vals],
        }
        invoice.write(invoice_values)
        logs += partner_logs + currency_logs + line_logs + allowance_charges_logs + rounding_logs
        return logs

    def _get_tax_nodes(self, tree):
        tax_nodes = tree.findall('.//{*}Item/{*}ClassifiedTaxCategory/{*}Percent')
        if not tax_nodes:
            for elem in tree.findall('.//{*}TaxTotal'):
                percentage_nodes = elem.findall('.//{*}TaxSubtotal/{*}TaxCategory/{*}Percent')
                if not percentage_nodes:
                    percentage_nodes = elem.findall('.//{*}TaxSubtotal/{*}Percent')
                tax_nodes += percentage_nodes
        return tax_nodes

    def _get_document_allowance_charge_xpaths(self):
        return {
            'root': './{*}AllowanceCharge',
            'charge_indicator': './{*}ChargeIndicator',
            'base_amount': './{*}BaseAmount',
            'amount': './{*}Amount',
            'reason': './{*}AllowanceChargeReason',
            'percentage': './{*}MultiplierFactorNumeric',
            'tax_percentage': './{*}TaxCategory/{*}Percent',
        }

    def _get_invoice_line_xpaths(self, document_type=False, qty_factor=1):
        return {
            'deferred_start_date': './{*}InvoicePeriod/{*}StartDate',
            'deferred_end_date': './{*}InvoicePeriod/{*}EndDate',
            'date_format': '%Y-%m-%d',
        }

    def _get_line_xpaths(self, document_type=False, qty_factor=1):
        return {
            'basis_qty': './cac:Price/cbc:BaseQuantity',
            'gross_price_unit': './{*}Price/{*}AllowanceCharge/{*}BaseAmount',
            'rebate': './{*}Price/{*}AllowanceCharge/{*}Amount',
            'net_price_unit': './{*}Price/{*}PriceAmount',
            'delivered_qty': (
                './{*}InvoicedQuantity'
                if document_type and document_type in ('in_invoice', 'out_invoice') or qty_factor == -1
                else './{*}CreditedQuantity'
            ),
            'allowance_charge': './/{*}AllowanceCharge',
            'allowance_charge_indicator': './{*}ChargeIndicator',
            'allowance_charge_amount': './{*}Amount',
            'allowance_charge_reason': './{*}AllowanceChargeReason',
            'allowance_charge_reason_code': './{*}AllowanceChargeReasonCode',
            'line_total_amount': './{*}LineExtensionAmount',
            'name': [
                './cac:Item/cbc:Description',
                './cac:Item/cbc:Name',
            ],
            'product': self._get_product_xpaths(),
        }

    def _get_product_xpaths(self):
        return {
            'default_code': './cac:Item/cac:SellersItemIdentification/cbc:ID',
            'name': './cac:Item/cbc:Name',
            'barcode': './cac:Item/cac:StandardItemIdentification/cbc:ID',
        }

    def _correct_invoice_tax_amount(self, tree, invoice):
        """ The tax total may have been modified for rounding purpose, if so we should use the imported tax and not
         the computed one """
        currency = invoice.currency_id
        # For each tax in our tax total, get the amount as well as the total in the xml.
        # Negative tax amounts may appear in invoices; they have to be inverted (since they are credit notes).
        document_amount_sign = self._get_import_document_amount_sign(tree)[1] or 1
        # We only search for `TaxTotal/TaxSubtotal` in the "root" element (i.e. not in `InvoiceLine` elements).
        for elem in tree.findall('./{*}TaxTotal/{*}TaxSubtotal'):
            percentage = elem.find('.//{*}TaxCategory/{*}Percent')
            if percentage is None:
                percentage = elem.find('.//{*}Percent')
            amount = elem.find('.//{*}TaxAmount')
            if (percentage is not None and percentage.text is not None) and (amount is not None and amount.text is not None):
                tax_percent = float(percentage.text)
                # Compare the result with our tax total on the invoice, and apply correction if needed.
                # First look for taxes matching the percentage in the xml.
                taxes = invoice.line_ids.tax_line_id.filtered(lambda tax: tax.amount == tax_percent)
                # If we found taxes with the correct amount, look for a tax line using it, and correct it as needed.
                if taxes:
                    tax_total = document_amount_sign * float(amount.text)
                    # Sometimes we have multiple lines for the same tax.
                    tax_lines = invoice.line_ids.filtered(lambda line: line.tax_line_id in taxes)
                    if tax_lines:
                        sign = -1 if invoice.is_inbound(include_receipts=True) else 1
                        tax_lines_total = currency.round(sign * sum(tax_lines.mapped('amount_currency')))
                        difference = currency.round(tax_total - tax_lines_total)
                        if not currency.is_zero(difference):
                            tax_lines[0].amount_currency += sign * difference
    # -------------------------------------------------------------------------
    # IMPORT : helpers
    # -------------------------------------------------------------------------

    def _get_import_document_amount_sign(self, tree):
        """
        In UBL, an invoice has tag 'Invoice' and a credit note has tag 'CreditNote'. However, a credit note can be
        expressed as an invoice with negative amounts. For this case, we need a factor to take the opposite
        of each quantity in the invoice.
        """
        if tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice':
            amount_node = tree.find('.//{*}LegalMonetaryTotal/{*}TaxExclusiveAmount')
            if amount_node is not None and float(amount_node.text) < 0:
                return 'refund', -1
            return 'invoice', 1
        if tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote':
            return 'refund', 1
        return None, None

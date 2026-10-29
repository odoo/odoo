from odoo import _, fields, models
from odoo.tools import formatLang, frozendict, html2plaintext, html_escape, float_round, unique
from lxml import etree

from odoo.addons.account.tools import dict_to_xml
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import EAS_MAPPING
from odoo.addons.l10n_si_edi_eslog.tools import EslogInvoice, EslogCreditNote, EslogDebitNote


class AccountEdiXmlEslog(models.AbstractModel):
    _inherit = 'account.edi.ubl'
    _name = 'account.edi.xml.eslog'
    _description = "e-SLOG 2.0"

    def _export_invoice_filename(self, invoice):
        return f"{invoice.name.replace('/', '_')}_eslog.xml"

    def _get_document_template(self, vals):
        return {
            'invoice': EslogInvoice,
            'credit_note': EslogCreditNote,
            'debit_note': EslogDebitNote,
        }[vals['document_type']]

    def _get_document_nsmap_eslog(self, vals):
        return {
            None: "urn:eslog:2.00",
            'xsi': "http://www.w3.org/2001/XMLSchema-instance",
        }

    def _export_invoice_constraints_new(self, invoice, vals):
        # OVERRIDE: don't apply normal UBL rules
        constraints = {}
        return constraints

    def _export_invoice(self, invoice, convert_fixed_taxes=True):
        # Use the new dict_to_xml helpers by default
        # unless the 'account_edi_ubl_cii.use_new_dict_to_xml_helpers' param is set to False.
        return self._export_invoice_new(invoice)

    def _export_invoice_new(self, invoice):
        """ Generates an UBL 2.0 xml for a given invoice, using the new dict_to_xml helpers. """
        # 1. Validate the structure of the taxes
        self._validate_taxes(invoice.invoice_line_ids.tax_ids)

        # 2. Instantiate the XML builder
        vals = {'invoice': invoice.with_context(lang=invoice.partner_id.lang)}
        document_node = self._get_invoice_node_eslog(vals)

        # 3. Run constraints
        vals['document_node'] = document_node
        template = self._get_document_template(vals)
        nsmap = document_node['_nsmap'] = self._get_document_nsmap_eslog(vals)
        errors = [constraint for constraint in self._export_invoice_constraints_new(invoice, vals).values() if constraint]

        # 4. Render the XML
        xml_content = dict_to_xml(document_node, nsmap=nsmap, template=template)

        # 5. Format the XML
        return etree.tostring(xml_content, xml_declaration=True, encoding='UTF-8', pretty_print=True), set(errors)

    def _get_invoice_node_eslog(self, vals):
        # OVERRIDE: separate document template
        vals.update({
            'accountant': 'deferred_start_date' in self.env['account.move.line'],
            'intrastat': 'intrastat_origin_country_id' in self.env['product.template'],
        })

        # These all match UBL 2.0. Can they be imported without dragging in too much unnecessary structure?
        self._add_invoice_config_vals(vals)
        self._add_invoice_base_lines_vals(vals)
        self._add_invoice_currency_vals(vals)
        self._add_invoice_tax_grouping_function_vals(vals)
        self._setup_base_lines(vals)
        self._add_document_monetary_total_vals(vals)

        base_lines_aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_tax_details(vals['base_lines'], vals['tax_grouping_function'])
        aggregated_tax_details = self.env['account.tax']._aggregate_base_lines_aggregated_values(base_lines_aggregated_tax_details)
        vals.update({'aggregated_tax_details': aggregated_tax_details})

        # Entirely independent chain as the format has nothing in common with UBL
        document_node = {}
        self._add_invoice_header_nodes_eslog(document_node, vals)
        self._add_invoice_accounting_customer_and_supplier_party_nodes_eslog(document_node, vals)  # Buyer comes first in eSlog
        #self._add_invoice_accounting_supplier_party_nodes(document_node, vals)

        if vals['document_type'] == 'invoice':
            #self._add_invoice_delivery_nodes(document_node, vals)
            #self._add_invoice_payment_means_nodes(document_node, vals)
            self._add_invoice_payment_terms_nodes_eslog(document_node, vals)

        self._add_invoice_currency_nodes_eslog(document_node, vals)
        self._add_invoice_allowance_charge_nodes_eslog(document_node, vals)
        self._add_invoice_line_nodes_eslog(document_node, vals)
        self._add_invoice_monetary_total_nodes_eslog(document_node, vals)
        self._add_invoice_tax_total_nodes_eslog(document_node, vals)

        return {'M_INVOIC': document_node}

    ### VALUES ###

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
                else 'credit_note' if invoice.move_type in ('out_refund', 'in_refund')
                else 'invoice',

            'company': invoice.company_id,
            'journal': invoice.journal_id,

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
        vals['base_lines'], _tax_lines = invoice._get_rounded_base_and_tax_lines()

    def _setup_base_lines(self, vals):
        base_lines = vals['base_lines']
        company = vals['company']

        for base_line in base_lines:
            # Allow retrieving the invoice line from the base_line.
            base_line['_invoice_line'] = base_line['record']
            line_name = base_line['record'] and base_line['record'].name
            base_line['_line_name'] = line_name and line_name.replace('\n', ' ')

            # Allow retrieving some custom values coming from manipulations of base lines.
            base_line['_ubl_values'] = {
                'recycling_contribution_taxes_data': [],
            }

        # Manage taxes for recycling contribution such as RECUPEL / AUVIBEL.
        self._dispatch_base_lines_recycling_contribution_taxes(base_lines, company, vals)

        # Manage taxes for emptying.
        base_lines = self._turn_emptying_taxes_as_new_base_lines(base_lines, company, vals)

        # Extract cash rounding lines.
        vals['base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] != 'cash_rounding']
        vals['cash_rounding_base_lines'] = [base_line for base_line in base_lines if base_line['special_type'] == 'cash_rounding']

    def _add_invoice_currency_vals(self, vals):
        self._add_document_currency_vals(vals)

    def _add_document_currency_vals(self, vals):
        """ Add the 'currency_suffix', 'currency_dp' and 'currency_name'. """
        vals['currency_suffix'] = '' if vals['use_company_currency'] else '_currency'

        currency = vals['company_currency_id'] if vals['use_company_currency'] else vals['currency_id']
        vals['currency_dp'] = self._get_currency_decimal_places(currency)
        vals['currency_name'] = currency.name

    def _add_invoice_tax_grouping_function_vals(self, vals):
        self._add_document_tax_grouping_function_vals(vals)

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

    def _dispatch_base_lines_recycling_contribution_taxes(self, base_lines, company, vals):
        """ Extract recycling contribution taxes such as RECUPEL, AUVIBEL, etc from the current base lines.
        Instead, add them under 'base_line' -> '_ubl_values' -> 'recycling_contribution_data' to be reported
        as allowances/charges.

        From a 'base_line' having
            price_unit = 99
            tax_ids = RECUPEL of 1 + 21% tax
            total_excluded_currency = 99
            total_included_currency = 121
            taxes_data = [1, 21]
            recycling_contribution_data = []
        ... turn it to:
            price_unit = 99
            tax_ids = 21% tax
            total_excluded_currency = 99
            total_included_currency = 121
            taxes_data = [21]
            recycling_contribution_data = [1]

        :param base_lines:  The original 'base_lines' of the document.
        :param company:     The company owning the 'base_lines'.
        :param vals:        Some custom data.
        """
        if not vals['fixed_taxes_as_allowance_charges']:
            return

        # Turn recycling contribution taxes into allowance/charge.
        # To distinguish them from emptying taxes, we know that one is taxed and not the other.
        def is_recycling_contribution(tax_data):
            if not tax_data:
                return

            tax = tax_data['tax']
            return tax.amount_type == 'fixed' and tax.include_base_amount

        for base_line in base_lines:
            tax_details = base_line['tax_details']
            taxes_data = tax_details['taxes_data']
            recycling_contribution_taxes_data = base_line['_ubl_values']['recycling_contribution_taxes_data']

            new_taxes_data = tax_details['taxes_data'] = []
            for tax_data in taxes_data:
                if is_recycling_contribution(tax_data):
                    recycling_contribution_taxes_data.append({'tax_data': tax_data})
                    tax_details['raw_total_excluded_currency'] += tax_data['raw_tax_amount_currency']
                    tax_details['raw_total_excluded'] += tax_data['raw_tax_amount']
                    tax_details['total_excluded_currency'] += tax_data['tax_amount_currency']
                    tax_details['total_excluded'] += tax_data['tax_amount']
                else:
                    new_taxes_data.append(tax_data)

    def _turn_emptying_taxes_as_new_base_lines(self, base_lines, company, vals):
        if not vals['fixed_taxes_as_allowance_charges']:
            return base_lines
        return self._ubl_turn_emptying_taxes_as_new_base_lines(base_lines, company, vals)

    def _add_invoice_monetary_totals_vals(self, vals):
        self._add_document_monetary_total_vals(vals)

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
            vals[f'total_tax_amount{currency_suffix}'] = sum(
                    tax_details[f'tax_amount{currency_suffix}']
                    for grouping_key, tax_details in aggregated_tax_details.items()
                    if grouping_key
                )
            vals[f'tax_inclusive_amount{currency_suffix}'] = vals[f'tax_exclusive_amount{currency_suffix}'] + vals[f'total_tax_amount{currency_suffix}']

        # Cash rounding for 'add_invoice_line' cash rounding strategy
        # (For the 'biggest_tax' strategy the amounts are directly included in the tax amounts.)
        for currency_suffix in ['', '_currency']:
            vals[f'cash_rounding_base_amount{currency_suffix}'] = 0.0
            for base_line in vals.setdefault('cash_rounding_base_lines', []):
                tax_details = base_line['tax_details']
                vals[f'cash_rounding_base_amount{currency_suffix}'] += tax_details[f'total_excluded{currency_suffix}']

    def _is_document_allowance_charge(self, base_line):
        """ Whether the base line should be treated as a document-level AllowanceCharge. """
        return base_line['special_type'] == 'early_payment'

    ### NODES ###

    def _add_invoice_header_nodes_eslog(self, document_node, vals):
        invoice = vals['invoice']

        document_node.update({
            "S_UNH": {
                "D_0062": {'_text': invoice.name},
                "C_S009": {
                    "D_0065": {'_text': 'INVOIC'} if vals['document_type'] == 'invoice' else None,
                    "D_0052": {'_text': 'D'},
                    "D_0054": {'_text': '01B'},
                    "D_0051": {'_text': 'UN'},
                },
            },
            "S_BGM": {
                "C_C002": {
                    "D_1001": {'_text': {'invoice': '380', 'credit_note': '381'}.get(vals['document_type'])},
                },
                "C_C106": {
                    "D_1004": {'_text': invoice.name},
                },
            },
            'S_DTM': [
                {"C_C507": {    # Document/message date/time
                    "D_2005": {'_text': '137'},
                    "D_2380": {'_text': invoice.invoice_date},
                }},
                {"C_C507": {    # Tax point date -> will possibly be replaced in the future
                    "D_2005": {'_text': '131'},
                    "D_2380": {'_text': invoice.date},
                }},
                {"C_C507": {    # 3 = Invoice date/time, 35 = Delivery date/time
                    "D_2005": {'_text': '35' if invoice.delivery_date else '3'},
                }},
                {"C_C507": {    # Delivery date/time, actual
                    "D_2005": {'_text': '35'},
                    "D_2380": {'_text': invoice.delivery_date},
                }} if invoice.delivery_date else None,
                {"C_C507": {    # Charge period start date
                    "D_2005": {'_text': '167'},
                    "D_2380": {'_text': min(line.deferred_start_date for line in invoice.invoice_line_ids if line.deferred_start_date)},
                }} if vals['accountant'] and any(line.deferred_start_date for line in invoice.invoice_line_ids) else None,
                {"C_C507": {    # Charge period end date
                    "D_2005": {'_text': '168'},
                    "D_2380": {'_text': max(line.deferred_end_date for line in invoice.invoice_line_ids if line.deferred_end_date)},
                }} if vals['accountant'] and any(line.deferred_end_date for line in invoice.invoice_line_ids) else None,
            ],
        })

        # Exemption reason should be the same for the whole document, so we just search for one pair
        aggregated_tax_details = vals['aggregated_tax_details']
        tax_exemption_reason = False
        tax_exemption_reason_code = False
        for grouping_key, values in aggregated_tax_details.items():
            if not grouping_key:
                continue
            tax_exemption_reason = grouping_key['tax_exemption_reason']
            tax_exemption_reason_code = grouping_key['tax_exemption_reason_code']
            if tax_exemption_reason and tax_exemption_reason_code:
                break

        document_node.update({
            "S_FTX": [
                {"D_4451": {'_text': "AAB"},
                 "C_C108": {
                    "D_4440": {'_text': html2plaintext(invoice.invoice_payment_term_id.note)},
                }},
                {"D_4451": {'_text': "REG" if vals['customer'].country_id.code != 'SI' else None},
                 "C_C108": {
                    "D_4440": {'_text': "Export" if vals['customer'].country_id.code != 'SI' else None},
                }},
                {"D_4451": {'_text': "DOC"},
                 "C_C107": {
                    "D_4441": {'_text': invoice.l10n_si_process_type},
                 },
                 "C_C108": {
                    "D_4440": {'_text': "urn:cen.eu:en16931:2017"},
                }},
                {"D_4451": {'_text': "AAT"},
                 "C_C108": {
                    "D_4440": {'_text': invoice.invoice_payment_term_id.name},
                }},
                {"D_4451": {'_text': "AGM"},
                 "C_C107": {
                    "D_4441": {'_text': tax_exemption_reason_code},
                 },
                 "C_C108": {
                    "D_4440": {'_text': tax_exemption_reason},
                }} if tax_exemption_reason_code else None,
                {"D_4451": {'_text': "PMD"},
                 "C_C108": {
                    "D_4440": {'_text': invoice.payment_reference},
                }} if invoice.payment_reference else None,
                {"D_4451": {'_text': "PAI"},
                 "C_C108": {
                    "D_4440": {'_text': '2' if invoice.payment_state == 'paid' else (
                        '1' if invoice.preferred_payment_method_line_id.code == 'sdd' else '0')},
                }},
            ],
        })
        document_node.update({
            "G_SG1": [
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': invoice.l10n_si_reference_type},
                        "D_1154": {'_text': invoice.ref if invoice.l10n_si_reference_type not in ['PQ', False] else invoice.payment_reference},
                    },
                }} if (invoice.l10n_si_reference_type != 'PQ' and invoice.ref) or
                      (invoice.l10n_si_reference_type == 'PQ' and invoice.payment_reference) else None,
                {"S_RFF": {
                    "C_C506": {
                        "D_2005": {'_text': "384"},
                        "D_2380": {'_text': invoice.reversed_entry_id.date},
                    },
                }} if invoice.l10n_si_reference_type == 'OI' else None,
            ],
        })

    def _add_invoice_accounting_customer_and_supplier_party_nodes_eslog(self, document_node, vals):
        invoice = vals['invoice']
        customer = vals['customer']
        supplier = vals['company'].partner_id
        customer_node = {
            "S_NAD": {
                "D_3035": {'_text': "BY"},
                "C_C082": {
                    "D_3039": {'_text': customer.peppol_endpoint},
                    "D_1131": {'_text': customer.peppol_eas},
                },
                "C_C080": {
                    "D_3036": {'_text': customer.name},
                    "D_3036_2": {'_text': customer.name},
                },
                "C_C059": {
                    "D_3042": {'_text': customer.street},
                    "D_3042_2": {'_text': customer.street2},
                },
                "D_3164": {'_text': customer.city},
                "D_3251": {'_text': customer.zip},
                "D_3207": {'_text': customer.country_id.code},
            },
            "S_FII": [
                {"D_3035": {'_text': "BI"},
                "C_C078": {
                    "D_3194": {'_text': invoice.journal_id.default_account_id.code},
                }},
                {"D_3035": {'_text': "BB"},
                "C_C078": {
                    "D_3194": {'_text': invoice.partner_bank_id.acc_number},
                    "D_3192": {'_text': invoice.partner_bank_id.acc_holder_name},
                },
                "C_C088": {
                    "D_3433": {'_text': invoice.partner_bank_id.bank_bic},
                }} if invoice.partner_bank_id else None,
            ],
            # A lot of the values here appear to refer to the payment details - after the payment is made, so can't be filled on send?
            "G_SG3": [
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': "CR"},
                        "D_1154": {invoice.commercial_partner_id.ref},
                    },
                }} if invoice.commercial_partner_id.ref else None,
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': customer.peppol_eas},
                        "D_1154": {'_text': customer.peppol_endpoint},
                    },
                }},
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': "VA"},
                        "D_1154": {'_text': customer.vat},
                    },
                }},
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': "AHP"},
                        "D_1154": {'_text': customer.vat},
                    },
                }},
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': "AVS"},
                        "D_1154": {'_text': invoice.sdd_mandate_id.name},
                    } if invoice.preferred_payment_method_line_id.code == 'sdd' else None,
                }},
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': "AII"},
                        "D_1154": {'_text': invoice.sdd_mandate_id.debtor_id_code},   # Bank transaction reference number
                    } if invoice.preferred_payment_method_line_id.code == 'sdd' else None,
                }},
            ],
            "G_SG5": [
                {"S_CTA": {
                    "D_3139": {'_text': "PD"},
                },
                "S_COM": {
                    "C_C076": {
                        "D_3148": {'_text': customer.email},
                        "D_3155": {'_text': "EM"},
                    },
                }} if customer.email else None,
            ],
        }
        supplier_node = {
            "S_NAD": {
                "D_3035": {'_text': "SE"},
                "C_C082": {
                    "D_3039": {'_text': supplier.peppol_endpoint},
                    "D_1131": {'_text': supplier.peppol_eas},
                },
                "C_C080": {
                    "D_3036": {'_text': supplier.name},
                    "D_3036_2": {'_text': supplier.name},
                },
                "C_C059": {
                    "D_3042": {'_text': supplier.street},
                    "D_3042_2": {'_text': supplier.street2},
                },
                "D_3164": {'_text': supplier.city},
                "D_3251": {'_text': supplier.zip},
                "D_3207": {'_text': supplier.country_id.code},
            },
            "G_SG3": [
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': supplier.peppol_eas},
                        "D_1154": {'_text': supplier.peppol_endpoint},
                    },
                }},
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': "VA"},
                        "D_1154": {'_text': supplier.vat},
                    },
                }},
                {"S_RFF": {
                    "C_C506": {
                        "D_1153": {'_text': "AHP"},
                        "D_1154": {'_text': supplier.vat},
                    },
                }},
            ],
            "G_SG5": [
                {"S_CTA": {     # Supplier contact -> keep
                    "D_3139": {'_text': "SU"},
                    "C_C056": {
                        "D_3412": {'_text': supplier.name},  # Seller contact point, Department or employee name
                    },
                },
                "S_COM": [
                    {"C_C076": {
                        "D_3148": {'_text': supplier.email},
                        "D_3155": {'_text': "EM"},
                    }} if supplier.email else None,
                    {"C_C076": {
                        "D_3148": {'_text': supplier.phone},
                        "D_3155": {'_text': "TE"},
                    }} if supplier.phone else None,
                ]} if supplier.email or supplier.phone else None,
            ],
        }
        document_node.update({
            'G_SG2': [customer_node, supplier_node],
        })

    def _add_invoice_currency_nodes_eslog(self, document_node, vals):
        invoice = vals['invoice']
        document_node.update({
            "G_SG7": [
                {"S_CUX": {
                    "C_C504": {
                        "D_6347": {'_text': '2'},
                        "D_6345": {'_text': invoice.currency_id.name},
                    },
                }},
                {"S_CUX": {
                    "C_C504": {
                        "D_6347": {'_text': '6'},
                        "D_6345": {'_text': invoice.company_id.currency_id.name},
                    },
                }},
            ],
        })

    def _add_invoice_payment_terms_nodes_eslog(self, document_node, vals):
        invoice = vals['invoice']
        payment_means_code_map = {  # Seems like very few things match
            'bank_account': "42",
            'card': "48",   # ?
            'ach_direct_debit': "49",   # ?
            'own_checks': "20",
            'new_third_party_checks': "20",
            'in_third_party_checks': "20",
            'out_third_party_checks': "20",
            'return_third_party_checks': "20",
            'sepa_ct': "58",
            'sdd': "59",
            'sepa_direct_debit': "59",
        }
        document_node.update({
            "G_SG8": {
                "S_PAT": {
                    "D_4279": {'_text': '1'},
                },
                "S_DTM": {
                    "C_C507": {
                        "D_2005": {'_text': '13'},
                        "D_2380": {'_text': invoice.invoice_date_due},
                    },
                },
                "S_PAI": {          # Payment means UNTDID 4461 code - not available when sending?
                    "C_C534": {     # -> same as SEPA, compute from invoice.preferred_payment_method_line_id.code
                        "D_4461": {'_text': payment_means_code_map.get(invoice.preferred_payment_method_line_id.code, "ZZZ")},
                    },
                },
            },
        })

    def _add_invoice_allowance_charge_nodes_eslog(self, document_node, vals):
        if vals['document_type'] != 'debit_note':
            document_node["G_SG16"] = []
            for base_line in vals['base_lines']:
                if self._is_document_allowance_charge(base_line):
                    document_node['cac:AllowanceCharge'].append(
                        self._get_document_allowance_charge_node_eslog({**vals, 'base_line': base_line})
                    )

    def _get_document_allowance_charge_node_eslog(self, vals):
        base_line = vals['base_line']
        currency_suffix = vals['currency_suffix']
        aggregated_tax_details = vals['aggregated_tax_details']
        base_amount = base_line['tax_details'][f'total_excluded{currency_suffix}']
        return {
            "G_SG16": {
                "S_ALC": {
                    "D_5463": {'_text': 'A' if base_amount < 0.0 else 'C'},   # -> Either positive or negative, one element
                    "C_C552": {
                        "D_1230": {'_text': _("Conditional cash/payment discount")},
                        "D_5189": {'_text': '66' if base_amount < 0.0 else 'ZZZ'},
                    },
                },
                #"G_SG19": {    # Document level allowance percentage may be used to calculate the document level allowance amount
                #    "S_PCD": {
                #        "C_C501": {
                #            "D_5245": {},
                #            "D_5482": {},
                #            "D_5249": {},
                #        },
                #        "D_4405": {},
                #    },
                #},
                "G_SG20": [
                    {"S_MOA": {
                        "C_C516": {
                            "D_5025": {'_text': '204' if base_amount < 0.0 else '23'},
                            "D_5004": {'_text': self.format_float(abs(base_amount), vals['currency_dp'])},
                        },
                    }},
                    {"S_MOA": {
                        "C_C516": {
                            "D_5025": {'_text': '25'},
                            "D_5004": {'_text': self.format_float(abs(base_line.amount_currency), vals['currency_dp'])},
                        },
                    }} if base_amount < 0.0 else None,
                ],
                "G_SG22": {
                    "S_TAX": {
                        "D_5283": {'_text': '7'},
                        "C_C241": {
                            "D_5153": {'VAT'},  # Always VAT now
                        },
                        "C_C243": {
                            "D_5278": {'_text': aggregated_tax_details['amount']},  # Check
                        },
                        "D_5305": {'_text': grouping_key['tax_category_code']
                                            for grouping_key in aggregated_tax_details
                                            if grouping_key},   # We need just one code per line here, would it always be one? -> one for VAT
                    },
                },
            },
        }

    def _add_invoice_line_nodes_eslog(self, document_node, vals):
        line_idx = 1
        #line_tag = self._get_tags_for_document_type(vals)['document_line']
        line_nodes = []
        for base_line in vals['base_lines']:
            if not self._is_document_allowance_charge(base_line):
                line_vals = {
                    **vals,
                    'line_idx': line_idx,
                    'base_line': base_line,
                }
                line_node = self._get_document_line_node_eslog(line_vals)
                line_nodes.append(line_node)
                line_idx += 1
        document_node['G_SG26'] = line_nodes

    def _get_document_line_node_eslog(self, vals):
        self._add_document_line_total_vals(vals)
        self._add_document_line_gross_subtotal_and_discount_vals(vals)
        invoice = vals['invoice']

        #tax_details = vals['tax_details']
        #grouping_key = vals['grouping_key']
        #sign = vals.get('sign', 1)
        currency_suffix = vals['currency_suffix']

        base_line = vals['base_line']
        product = base_line['product_id']
        product_price_dp = self.env['decimal.precision'].precision_get('Product Price')
        tax = base_line['tax_ids'][0]  # We need line tax details here, we don't have access to grouping_key, and there should only be one anyway
        return {
            "S_LIN": {
                "D_1082": {'_text': vals['line_idx']},
                "C_C212": {
                    "D_7140": {'_text': product.barcode},
                    "D_7143": {'_text': "0160"},  # GTIN
                },
                "C_C829": {
                    "D_5495": {},
                    "D_1082": {},
                },
                "D_1222": {},
                "D_7083": {},
            },
            "S_PIA": {
                "D_4347": {'_text': "5"} if product.default_code else None,
                "C_C212": {
                    "D_7140": {'_text': product.default_code},
                    "D_7143": {'_text': 'SA'},
                } if product.default_code else None,
                # There is also an "Additional product id" optional section, which uses UNTDID 7143 code 'ZZZ'
                # defined as "Item type identification mutually agreed between interchanging parties" -> ignore
            },
            "S_IMD": {
                "D_7077": {'_text': "F"},
                "C_C273": {
                    "D_7008": {'_text': product.description_sale},
                },
            },
            "S_QTY": {
                "C_C186": {
                    "D_6063": {'_text': "47"},
                    "D_6060": {'_text': base_line['quantity']},
                    "D_6411": {'_text': self._get_uom_unece_code(base_line['product_uom_id'])},
                },
            },
            "S_ALI": {  # The code identifying the country from which the item originates
                "D_3239": {'_text': product.intrastat_origin_country_id.code},
            } if vals['intrastat'] else None,
            "S_DTM": [
                {"C_C507": {
                    "D_2005": {'_text': "167"},   # Charge period start date
                    "D_2380": {'_text': base_line['_invoice_line'].deferred_start_date},
                }} if base_line['_invoice_line'].deferred_start_date else None,
                {"C_C507": {
                    "D_2005": {'_text': "168"},   # Charge period end date
                    "D_2380": {'_text': base_line['_invoice_line'].deferred_end_date},
                }} if base_line['_invoice_line'].deferred_end_date else None,
            ] if vals['accountant'] else None,
            "S_FTX": [
                {"D_4451": {'_text': "ACF"},
                 "C_C108": {
                    "D_4440": {'_text': value.attribute_id.name},
                    "D_4440_2": {'_text': value.name},
                }} for value in product.product_template_attribute_value_ids
            ],
            "G_SG27": [
                {"S_MOA": {
                    "C_C516": {
                        "D_5025": {'_text': "203"},
                        "D_5004": {'_text': float_round(
                            vals['gross_subtotal_currency'],
                            precision_digits=product_price_dp,
                        )},
                    },
                }},
                {"S_MOA": {
                    "C_C516": {
                        "D_5025": {'_text': "38"},
                        "D_5004": {'_text': float_round(
                            vals['gross_subtotal_currency'] + vals[f'total_fixed_taxes{currency_suffix}'],   # Check
                            precision_digits=product_price_dp,
                        )},
                    },
                }},
            ],
            "G_SG29": [
                {"S_PRI": {
                    "C_C509": {
                        "D_5125": {'_text': "AAA"},
                        "D_5118": {'_text': float_round(
                            base_line['currency_id'].round(base_line['price_unit'] * base_line['quantity']) / base_line['quantity'],
                            precision_digits=product_price_dp,
                        )},
                        "D_5284": {'_text': base_line['product_uom_id'].factor},
                        "D_6411": {'_text': self._get_uom_unece_code(base_line['product_uom_id'])},
                    },
                }},
                {"S_PRI": {
                    "C_C509": {
                        "D_5125": {'_text': "AAB"},
                        "D_5118": {'_text': float_round(
                            base_line['price_unit'],
                            precision_digits=product_price_dp,
                        )},
                        "D_5284": {'_text': base_line['quantity']},
                        "D_6411": {'_text': self._get_uom_unece_code(base_line['product_uom_id'])},
                    },
                }},
            ],
            "G_SG30": {
                "S_RFF": [
                    {"C_C506": {     # "An identifier for an object on which the invoice line is based, given by the Seller"
                        "D_1153": {'_text': "AVE"},
                        "D_1154": {'_text': product.default_code},
                    }} if product.default_code else None,
                    {"C_C506": {
                        "D_1153": {'_text': "ON"},
                        "D_1156": {'_text': invoice.ref},    # Order number is invoice-level, therefore applied to all items?
                    }} if invoice.l10n_si_reference_type == 'ON' else None,
                ],
            },
            "G_SG34": {
                "S_TAX": {
                    "D_5283": {'_text': "7"},
                    "C_C241": {
                        "D_5153": {'_text': "VAT"},
                    },
                    "C_C243": {
                        #"D_5278": {'_text': grouping_key['amount'] if grouping_key['amount_type'] == 'percent' else None},
                        "D_5278": {'_text': tax.amount if tax.amount_type == 'percent' else None},
                    },
                    #"D_5305": {'_text': grouping_key['tax_category_code']},
                    "D_5305": {'_text': self._get_tax_category_code(vals['customer'], vals['supplier'], tax)},
                },
                "S_MOA": [
                    {"C_C516": {    # "Taxable amount"
                        "D_5025": {'_text': "125"},
                        "D_5004": {'_text': float_round(
                            vals['gross_subtotal_currency'],
                            precision_digits=product_price_dp,
                        )},
                    }},
                    {"C_C516": {    # "Tax amount" - Line total taxes
                        "D_5025": {'_text': "124"},
                        "D_5004": {'_text': float_round(
                            vals[f'total_fixed_taxes{currency_suffix}'],
                            precision_digits=product_price_dp,
                        )},
                    }},
                ],
            },
            "G_SG39": {
                "S_ALC": {
                    "D_5463": {'_text': 'A' if vals[f'discount_amount{currency_suffix}'] > 0.0 else 'C'},   # Check sign
                    "C_C552": {
                        "D_1230": {'_text': _("Conditional cash/payment discount")},
                        "D_5189": {'_text': '66' if vals[f'discount_amount{currency_suffix}'] > 0.0 else 'ZZZ'},
                    },
                },
                #"G_SG41": {
                #    "S_PCD": {
                #        "C_C501": {
                #            "D_5245": {'_text': '1' if vals[f'discount_amount{currency_suffix}'] > 0.0 else '2'},
                #            "D_5482": {},   # Allowance percentage -> ignore
                #        },
                #    },
                #},
                "G_SG42": [
                    {"S_MOA": {
                        "C_C516": {
                            "D_5025": {'_text': '204' if vals[f'discount_amount{currency_suffix}'] > 0.0 else '23'},
                            "D_5004": {'_text': vals[f'discount_amount{currency_suffix}']},
                        },
                    }},
                    {"S_MOA": {
                        "C_C516": {
                            "D_5025": {'_text': '25'},
                            "D_5004": {'_text': vals['gross_subtotal_currency']},
                        },
                    }},
                    {"S_MOA": {
                        "C_C516": {
                            "D_5025": {'_text': '509'},
                            "D_5004": {'_text': vals[f'discount_amount{currency_suffix}'] / base_line['quantity']},
                        } if vals[f'discount_amount{currency_suffix}'] > 0.0 else None,
                    }},
                ],
            },
        }

    def _add_document_line_total_vals(self, vals):  # Import from UBL 2.0?
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

    def _add_document_line_gross_subtotal_and_discount_vals(self, vals):    # Import from UBL 2.0?
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

    def _add_invoice_monetary_total_nodes_eslog(self, document_node, vals):
        aggregated_tax_details = vals['aggregated_tax_details']
        currency_suffix = vals['currency_suffix']
        document_node.update({
            #"S_UNS": {  # Optional separator
            #    "D_0081": {'_text': "D"},
            #},
            "G_SG50": [
                {"S_MOA": {
                    "C_C516": {    # "Total line items amount"
                        "D_5025": {'_text': "79"},
                        "D_5004": {'_text': self.format_float(vals[f'tax_exclusive_amount{currency_suffix}'], vals['currency_dp'])},
                    },
                }},
                {"S_MOA": {
                    "C_C516": {    # "Amount excluding Value Added Tax (VAT)" - same value in documentation
                        "D_5025": {'_text': "389"},
                        "D_5004": {'_text': self.format_float(vals[f'tax_exclusive_amount{currency_suffix}'], vals['currency_dp'])},
                    },
                }},
                {"S_MOA": {
                    "C_C516": {    # "Total amount including Value Added Tax (VAT)"
                        "D_5025": {'_text': "388"},
                        "D_5004": {'_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp'])},
                    },
                }},
                {"S_MOA": {
                    "C_C516": {    # "Amount due/amount payable"
                        "D_5025": {'_text': "388"},
                        "D_5004": {'_text': self.format_float(vals[f'tax_inclusive_amount{currency_suffix}'], vals['currency_dp'])},
                    },
                }},
                {"S_MOA": {
                    "C_C516": {    # "Total allowances"
                        "D_5025": {'_text': "260"},
                        "D_5004": {'_text': self.format_float(vals[f'total_allowance{currency_suffix}'], vals['currency_dp'])},
                    } if vals[f'total_allowance{currency_suffix}'] else None,
                }},
                {"S_MOA": {
                    "C_C516": {    # "Total charges"
                        "D_5025": {'_text': "259"},
                        "D_5004": {'_text': self.format_float(vals[f'total_charge{currency_suffix}'], vals['currency_dp'])},
                    } if vals[f'total_charge{currency_suffix}'] else None,
                }},
                {"S_MOA": {
                    "C_C516": {    # "VAT, 2nd value" - appears to be VAT in seller currency
                        "D_5025": {'_text': "2"},     # Applies when SI invoices non-EUR customers -> convert from invoice to company currency
                        "D_5004": {
                            '_text': self.format_float(
                                vals.get('sign', 1) * sum(
                                    values['tax_amount']    # Should be "default" currency - company currency?
                                    for grouping_key, values in aggregated_tax_details.items()
                                    if grouping_key
                                ),
                                self._get_currency_decimal_places(vals['company_currency_id'])),
                        },
                    },
                }},
                {"S_MOA": {
                    "C_C516": {    # "Prepaid amount" - is set to zero in UBL
                        "D_5025": {'_text': "113"},
                        "D_5004": {'_text': self.format_float(0.0, vals['currency_dp'])},
                    },
                }},
                {"S_MOA": {
                    "C_C516": {    # "Rounding amount"
                        "D_5025": {'_text': "366"},
                        "D_5004": {'_text': self.format_float(vals[f'cash_rounding_base_amount{currency_suffix}'], vals['currency_dp'])},
                    } if vals[f'cash_rounding_base_amount{currency_suffix}'] else None,
                }},
                {"S_MOA": {
                    "C_C516": {    # "Message total duty/tax/fee amount"
                        "D_5025": {'_text': "176"},
                        "D_5004": {
                            '_text': self.format_float(
                                vals.get('sign', 1) * sum(
                                    values[f'tax_amount{currency_suffix}']
                                    for grouping_key, values in aggregated_tax_details.items()
                                    if grouping_key
                                ),
                                vals['currency_dp']),
                        },
                    },
                }},
            ],
        })

    def _add_invoice_tax_total_nodes_eslog(self, document_node, vals):
        #company_currency = vals['invoice'].company_id.currency_id   # Should be set for SI?
        aggregated_tax_details = vals['aggregated_tax_details']
        #print("--- DEBUG: aggregated_tax_details:", aggregated_tax_details.items(), "---")
        tax_subtotal_nodes = [
            self._get_tax_subtotal_node_eslog({
                **vals,
                'tax_details': tax_details,
                'grouping_key': grouping_key,
            })
            for grouping_key, tax_details in aggregated_tax_details.items()
            if grouping_key
        ]
        document_node["G_SG52"] = tax_subtotal_nodes

    def _get_tax_subtotal_node_eslog(self, vals):
        tax_details = vals['tax_details']
        grouping_key = vals['grouping_key']
        sign = vals.get('sign', 1)
        currency_suffix = vals['currency_suffix']
        return {
            "S_TAX": {  # "7" is VAT, OTH is used in Peppol for fixed taxes
                "D_5283": {'_text': "7" if grouping_key['amount_type'] == 'percent' else "OTH"},
                "C_C243": {     # Tax percentage
                    "D_5278": {'_text': grouping_key['amount']} if grouping_key['amount_type'] == 'percent' else None,
                },
                "D_5305": {'_text': grouping_key['tax_category_code']},
            },
            "S_MOA": [
                {"C_C516": {
                    "D_5025": {'_text': "125"},    # Taxable amount
                    "D_5004": {'_text': self.format_float(tax_details[f'base_amount{currency_suffix}'], vals['currency_dp'])},
                }},
                {"C_C516": {
                    "D_5025": {'_text': "124"},    # Tax amount
                    "D_5004": {'_text': self.format_float(sign * tax_details[f'tax_amount{currency_suffix}'], vals['currency_dp'])},
                }},
            ],
        }

    ### IMPORT ###

    def _import_eslog_invoice_add_customer_values(self, collected_values):
        customer_values = collected_values['customer_values'] = {}
        odoo_document_type = collected_values['odoo_document_type']
        party_tag = "BY" if odoo_document_type == 'sale' else "SE"
        tree = collected_values['tree']
        # Get the SG2 node and import everything here, no point in splitting it up if it's not reusable?
        party_node = tree.find(f"./{{*}}Party[text()={party_tag}]")
        if party_node is None:
            return

        # UBL: Only take the CompanyID of a PartyTaxScheme using a VAT scheme (e.g. not the Peppol endpoint with its EAS)
        customer_values['vat'] = next((
            node.findtext('./{*}D_1154')
            for node in party_node.iterfind('./{*}C_C506')
            if (node.findtext('./{*}D_1153') or '').upper() in ('VA', 'AHP')    # "Tax registration number" should apply?
        ), None)
        customer_values['email'] = next((
            node.findtext('./{*}D_3148')
            for node in party_node.iterfind('./{*}C_C076')
            if (node.findtext('./{*}D_3155') or '').upper() == 'TE'
        ), None)
        customer_values['email'] = next((
            node.findtext('./{*}D_3148')
            for node in party_node.iterfind('./{*}C_C076')
            if (node.findtext('./{*}D_3155') or '').upper() == 'EM'
        ), None)

        for key, xpaths in (
            ('name', [".//{*}D_3036"]),
            ('country_code', [".//{*}D_3207"]),
            ('street', [".//{*}D_3042"]),
            ('street2', [".//{*}D_3042_2"]),
            ('city', [".//{*}D_3164"]),
            ('zip', [".//{*}D_3251"]),
        ):
            customer_values[key] = None
            for xpath in xpaths:
                if (node := party_node.find(xpath)) is not None:
                    customer_values[key] = node.text
                    break

        (customer_values['peppol_eas'], customer_values['peppol_endpoint']) = next((
            (node.findtext('./{*}D_1153'), node.findtext('./{*}D_1154'))
            for node in party_node.iterfind('./{*}C_C506')
            if (node.findtext('./{*}D_1153') or '').upper() in EAS_MAPPING.get(customer_values.get('country_code'), {})
        ), None)

    def _import_eslog_invoice_add_currency_values(self, collected_values):
        currency_values = collected_values['currency_values'] = {}
        tree = collected_values['tree']
        currency_values['currency_code'] = tree.findtext('.//{*}D_6345')

    def _import_eslog_invoice_add_dates(self, collected_values):
        tree = collected_values['tree']
        date_node = tree.find("./{{*}}S_DTM")
        date_values = {}
        date_values['invoice_date'] = next((
            node.findtext('./{*}D_2380')
            for node in date_node.iterfind('./{*}C_C507')
            if (node.findtext('./{*}D_2005') or '').upper() == '137'
        ), None)
        date_values['date'] = next((
            node.findtext('./{*}D_2380')
            for node in date_node.iterfind('./{*}C_C507')
            if (node.findtext('./{*}D_2005') or '').upper() == '131'
        ), None)
        date_values['delivery_date'] = next((
            node.findtext('./{*}D_2380')
            for node in date_node.iterfind('./{*}C_C507')
            if (node.findtext('./{*}D_2005') or '').upper() == '35'
        ), None) or ''
        # There are boundary deferred start and end dates extractable from 167 and 168
        # Due date is not part of the same DTM node
        date_values['invoice_date_due'] = next((
            node.findtext('./{*}D_2380')
            for node in tree.iterfind('./{*}G_SG8//{*}C_C507')
            if (node.findtext('./{*}D_2005') or '').upper() == '13'
        ), None) or ''
        for key, value in date_values.items():
            if value:
                collected_values['to_write'][key] = fields.Date.from_string(value)

    def _import_eslog_invoice_add_partner_bank_values(self, collected_values):
        partner_bank_values = collected_values['partner_bank_values'] = {}
        tree = collected_values['tree']
        (account_number, account_holder_name) = next((
            (node.findtext('./{*}D_3194'), node.findtext('./{*}D_3192'))
            for node in tree.iterfind('./{*}C_C078')
            if (node.findtext('./{*}D_1153') or '').upper() == 'BB'
        ), None)
        # Bank BIC can be retrieved from C_C088/D_3433

        partner_bank_values['account_numbers'] = account_number

    def _import_eslog_invoice_add_ref(self, collected_values):
        tree = collected_values['tree']
        si_reference_type = tree.findtext('.//{*}G_SG1/{*}S_RFF/{*}C_C506/{*}D_1153')
        if si_reference_type:
            collected_values['to_write']['l10n_si_reference_type'] = si_reference_type
        odoo_document_type = collected_values['odoo_document_type']
        if ref := tree.findtext('.//{*}G_SG1/{*}S_RFF/{*}C_C506/{*}D_1154'):
            if odoo_document_type == 'sale' and collected_values['invoice'].quick_edit_mode:
                collected_values['to_write']['name'] = ref
            else:
                collected_values['to_write']['ref'] = ref

    def _import_eslog_invoice_add_narration(self, collected_values):
        tree = collected_values['tree']
        notes = []
        note_texts = (
            node.findtext('./{*}C_C108/{*}D_4440')
            for node in tree.findall('.//{*}S_FTX')
            if (node.findtext('./{*}C_C108/{*}D_4451') or '').upper() == 'AAB'
        )
        for item in note_texts:
            if item:
                notes.append(html_escape(item))

        if narration := ''.join(f'<p>{note}</p>' for note in notes):
            collected_values['to_write']['narration'] = narration

    def _import_eslog_invoice_add_payment_reference(self, collected_values):
        tree = collected_values['tree']
        payment_references = []
        payment_reference_texts = (
            node.findtext('./{*}C_C108/{*}D_4440')
            for node in tree.findall('.//{*}S_FTX')
            if (node.findtext('./{*}C_C108/{*}D_4451') or '').upper() == 'PMD'
        )
        for item in payment_reference_texts:
            if item:
                payment_references.append(html_escape(item))

        if payment_reference := ','.join(unique(payment_references)):
            collected_values['to_write']['payment_reference'] = payment_reference

    def _import_eslog_invoice_add_prepaid_amount(self, collected_values):
        file_document_sign = collected_values['file_document_sign']
        currency = collected_values['currency_values']['currency']
        tree = collected_values['tree']
        prepaid_amount_str = next((
            node.findtext('./{*}D_5004')
            for node in tree.iterfind('./{*}G_SG50/{*}S_MOA/{*}/{*}C_516')
            if (node.findtext('./{*}D_5025') or '').upper() == '113'
        ), None)
        prepaid_amount = file_document_sign * float(prepaid_amount_str or 0.0)
        if currency.is_zero(prepaid_amount):
            return

        collected_values['prepaid_amount'] = prepaid_amount
        formatted_prepaid_amount = formatLang(self.env, prepaid_amount, currency_obj=currency)
        collected_values['logs'].append(_("A payment of %s was detected.", formatted_prepaid_amount))

    def _import_ubl_invoice_add_tax_total_values(self, collected_values):
        file_document_sign = collected_values['file_document_sign']
        odoo_document_type = collected_values['odoo_document_type']

        taxes_values = collected_values['tax_total_values'] = {}
        tree = collected_values['tree']
        for subtotal_elem in tree.findall('./{*}TaxTotal/{*}TaxSubtotal'):
            amount = subtotal_elem.findtext('.//{*}TaxAmount')
            category_code = subtotal_elem.findtext('.//{*}TaxCategory/{*}ID')
            if amount is None or category_code is None:
                continue

            percentage = subtotal_elem.findtext('.//{*}TaxCategory/{*}Percent')
            if percentage is None:
                percentage = subtotal_elem.findtext('.//{*}Percent')
            if percentage is None:
                continue

            percentage = float(percentage)
            tax_key = frozendict({
                'category_code': category_code,
                'percentage': percentage,
            })
            tax_values = taxes_values.setdefault(tax_key, {
                'amount_type': 'percent',
                'type_tax_use': odoo_document_type,
                'amount': percentage,
                'ubl_cii_tax_category_code': category_code,
                'tax_amount_currency': 0.0,
                'related_taxes_values': [],
            })
            tax_values['tax_amount_currency'] += file_document_sign * float(amount)

    def _import_eslog_invoice_add_allowances_charges_values(self, collected_values):
        tree = collected_values['tree']
        odoo_document_type = collected_values['odoo_document_type']
        allowances = collected_values['allowances'] = []
        charges = collected_values['charges'] = []
        taxes_values = collected_values['taxes_values'] = []
        tax_total_values = collected_values['tax_total_values']

        for element in tree.iterfind('./{*}G_SG16'):
            reason = element.findtext('./{*}AllowanceChargeReason')
            reason_code = element.findtext('./{*}AllowanceChargeReasonCode')
            charge_indicator = element.findtext('./{*}S_ALC/{*}D_5463')     # Conditional, 'A' if base_amount < 0.0 else 'C'
            amount_str = next((
                node.findtext('./{*}D_5004')
                for node in element.iterfind('./{*}G_SG20/{*}S_MOA/{*}/{*}C_516')
                if (node.findtext('./{*}D_5025') or '').upper() in ('204', '23')
            ), None)
            base_amount_str = next((
                node.findtext('./{*}D_5004')
                for node in element.iterfind('./{*}G_SG20/{*}S_MOA/{*}/{*}C_516')
                if (node.findtext('./{*}D_5025') or '').upper() == '25'
            ), None)
            percentage_str = element.findtext('./{*}G_SG22/{*}S_TAX/{*}C_C243/{*}D_5278')
            category_code = element.findtext('./{*}G_SG22/{*}S_TAX/{*}D_5305')

            if amount_str:
                amount = float(amount_str)
            else:
                amount = 0.0

            if not percentage_str:
                continue

            percentage = float(percentage_str)
            allowance_charge_values = {
                'amount': amount,
                'base_amount': float(base_amount_str) if base_amount_str else None,
                'reason': reason,
                'reason_code': reason_code,
                'tax_percentage': percentage,
                'charge_indicator': charge_indicator,
            }

            tax_category_tree = element.find('./{*}TaxCategory')
            tax_values = self._import_ubl_invoice_line_prepare_classified_tax_category_tax_values(collected_values, tax_category_tree)
            if tax_values:
                allowance_charge_values['taxes_values'] = tax_values
                global_tax_values = tax_total_values.get(tax_values['_tax_key'])
                global_tax_values['related_taxes_values'].append(tax_values)

            if charge_indicator.lower() == 'true':
                charges.append(allowance_charge_values)
            else:
                allowances.append(allowance_charge_values)

            # Try to link the allowance / charge with a percentage tax.
            if not category_code:
                continue

            tax_key = frozendict({
                'category_code': category_code,
                'percentage': percentage,
            })
            allowance_charge_values['attempt_tax_values'] = tax_values = {
                'amount_type': 'percent',
                'type_tax_use': odoo_document_type,
                'ubl_cii_tax_category_code': category_code,
                'amount': percentage,
                '_tax_key': tax_key,
            }
            taxes_values.append(tax_values)

    def _import_eslog_invoice_line_add_values(self, collected_values):
        file_document_sign = collected_values['file_document_sign']
        line_tree = collected_values['line_tree']   # Invoice lines are within G_SG26

        #item_ref = line_tree.findtext('./{*}S_PIA/{*}C_C212/{*}D_7140')
        item_name = next((
            node.findtext('./{*}D_7140')
            for node in line_tree.iterfind('./{*}S_PIA/{*}C_C212')
            if (node.findtext('./{*}D_7143') or '').upper() == 'SA'
        ), None)
        item_description = next((
            node.findtext('./{*}D_7008')
            for node in line_tree.iterfind('./{*}S_IMD/{*}C_C273')
            if (node.findtext('./{*}D_7077') or '').upper() == 'F'
        ), None)
        name = collected_values['name'] = (
            item_description
            or item_name #(f"[{item_ref}] {item_name}" if (item_ref and item_name) else item_name)
        )
        if name:
            collected_values['to_write']['name'] = name

        currency = collected_values['currency_values']['currency']

        line_extension_amount_str = line_tree.findtext('.//{*}LineExtensionAmount')
        price_amount_str = line_tree.findtext('.//{*}Price/{*}PriceAmount')
        invoiced_quantity_str = (
            line_tree.findtext('.//{*}InvoicedQuantity')
            or line_tree.findtext('.//{*}CreditedQuantity')
        )
        base_quantity_str = line_tree.findtext('./{*}Price/{*}BaseQuantity')
        line_extension_amount = line_extension_amount_str and float(line_extension_amount_str) * file_document_sign
        price_amount = price_amount_str and float(price_amount_str)
        invoiced_quantity = invoiced_quantity_str and float(invoiced_quantity_str) * file_document_sign
        base_quantity = base_quantity_str and float(base_quantity_str)

        total_allowances = sum(allowance['amount'] for allowance in collected_values['allowances'])
        total_charges = sum(charge['amount'] for charge in collected_values['charges'])
        price_allowance_values = collected_values['price_allowance_values']
        price_allowance_base_amount = price_allowance_values.get('base_amount')
        price_allowance_amount = price_allowance_values.get('amount')
        if price_allowance_amount and (price_allowance_charge_indicator_sign := price_allowance_values.get('charge_indicator_sign')):
            price_allowance_amount *= price_allowance_charge_indicator_sign
        subtotal = (line_extension_amount or 0.0) + total_allowances - total_charges

        # Price level.
        # Define at the product level the price for which quantity and how many discount you get
        # by buying it
        if price_amount:
            price_quantity = base_quantity or 1.0
            if price_allowance_base_amount:
                price_discount_amount = price_allowance_base_amount - price_amount
                price_subtotal = price_allowance_base_amount
            elif price_allowance_amount:
                price_discount_amount = -price_allowance_amount
                price_subtotal = price_amount - price_allowance_amount
            else:
                price_discount_amount = 0.0
                price_subtotal = price_amount
        elif price_allowance_base_amount:
            price_subtotal = price_allowance_base_amount
            price_quantity = base_quantity or 1.0
            price_discount_amount = -(price_allowance_amount or 0.0)
        else:
            price_subtotal = 0.0
            price_quantity = 0.0
            price_discount_amount = 0.0

        # Line level.
        if (
            line_extension_amount is not None
            and not invoiced_quantity
        ):
            price_unit = subtotal
            quantity = 1.0
            discount_amount = total_allowances

            # Combine with the price level. Suppose:
            # line_extension_amount = 1000.0
            # price_subtotal = 1250.0
            # price_quantity = 5.0
            # price_discount_amount = 250.0
            # In that case, we want to compute:
            # price_unit = 250.0
            # quantity = 5.0
            # discount_amount = 250.0
            if not currency.is_zero(price_subtotal):
                quantity = subtotal * price_quantity / (price_subtotal - price_discount_amount)
                if quantity:
                    price_unit = (subtotal / quantity) + (price_discount_amount / price_quantity)
                else:
                    price_unit = price_amount
                discount_amount += price_discount_amount * quantity / price_quantity

        elif (
            line_extension_amount is not None
            and invoiced_quantity
        ):
            quantity = invoiced_quantity
            price_unit = subtotal / quantity
            discount_amount = total_allowances

            # Combine with the price level. Suppose:
            # line_extension_amount = 1200.0
            # quantity = 6
            # price_subtotal = 1250.0
            # price_quantity = 5.0
            # price_discount_amount = 50.0
            # In that case, we want to compute:
            # price_unit = 250.0
            # quantity = 6.0
            # discount_amount = 300.0
            if not currency.is_zero(price_subtotal):
                price_unit = price_subtotal / price_quantity
                discount_amount += price_discount_amount * quantity / price_quantity
        else:
            quantity = 0.0
            price_unit = 0.0
            discount_amount = total_allowances

            # Combine with the price level.
            if not currency.is_zero(price_subtotal):
                price_unit = price_subtotal / price_quantity
                quantity = price_quantity
                discount_amount += price_discount_amount

        # Extra charges.
        price_unit += total_charges / (quantity or 1.0)

        # Turn discount_amount to a percentage
        gross_subtotal = price_unit * quantity
        discount = (discount_amount * 100 / gross_subtotal) if gross_subtotal else 0.0

        to_write = collected_values['to_write']
        to_write['quantity'] = quantity
        to_write['price_unit'] = price_unit
        to_write['discount'] = discount

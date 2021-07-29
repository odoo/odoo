# -*- coding: utf-8 -*-
from collections import defaultdict
from pathlib import PureWindowsPath

from odoo import models, _
from odoo.osv import expression
from odoo.tests.common import Form
from odoo.tools import html2plaintext


class AccountEdiXmlUBL20(models.AbstractModel):
    _name = "account.edi.xml.ubl_20"
    _inherit = 'account.edi.xml'
    _description = "UBL 2.0"

    # -------------------------------------------------------------------------
    # EXPORT
    # -------------------------------------------------------------------------

    def _get_country_vals(self, country):
        return {
            'country': country,

            'identification_code': country.code,
            'name': country.name,
        }

    def _get_partner_party_identification_vals_list(self, partner):
        return []

    def _get_partner_address_vals(self, partner):
        return {
            'street_name': partner.street,
            'additional_street_name': partner.street2,
            'city_name': partner.city,
            'postal_zone': partner.zip,
            'country_subentity': partner.state_id.name,
            'country_subentity_code': partner.state_id.code,
            'Country_vals': self._get_country_vals(partner.country_id),
        }

    def _get_partner_party_tax_scheme_vals(self, partner):
        return {
            'registration_name': partner.name,
            'company_id': partner.vat,
            'RegistrationAddress_vals': self._get_partner_address_vals(partner),
            'TaxScheme_vals': {},
        }

    def _get_partner_party_legal_entity_vals(self, partner):
        commercial_partner = partner.commercial_partner_id

        return {
            'commercial_partner': commercial_partner,

            'registration_name': commercial_partner.name,
            'company_id': commercial_partner.vat,
            'RegistrationAddress_vals': self._get_partner_address_vals(commercial_partner),
        }

    def _get_partner_contact_vals(self, partner):
        return {
            'id': partner.id,
            'name': partner.name,
            'telephone': partner.phone or partner.mobile,
            'electronic_mail': partner.email,
        }

    def _get_partner_party_vals(self, partner):
        return {
            'partner': partner,
            'PartyIdentification_vals': self._get_partner_party_identification_vals_list(partner),
            'PartyName_vals': [{'name': partner.name}],
            'PostalAddress_vals': self._get_partner_address_vals(partner),
            'PartyTaxScheme_vals': self._get_partner_party_tax_scheme_vals(partner),
            'PartyLegalEntity_vals': self._get_partner_party_legal_entity_vals(partner),
            'Contact_vals': self._get_partner_contact_vals(partner),
        }

    def _get_bank_address_vals(self, bank):
        return {
            'street_name': bank.street,
            'additional_street_name': bank.street2,
            'city_name': bank.city,
            'postal_zone': bank.zip,
            'country_subentity': bank.state.name,
            'country_subentity_code': bank.state.code,
            'Country_vals': self._get_country_vals(bank.country),
        }

    def _get_financial_institution_vals(self, bank):
        return {
            'bank': bank,

            'id': bank.bic,
            'id_attrs': {'schemeID': 'BIC'},
            'name': bank.name,
            'Address_vals': self._get_bank_address_vals(bank),
        }

    def _get_financial_institution_branch_vals(self, bank):
        return {
            'bank': bank,

            'id': bank.bic,
            'id_attrs': {'schemeID': 'BIC'},
            'FinancialInstitution_vals': self._get_financial_institution_vals(bank),
        }

    def _get_financial_account_vals(self, partner_bank):
        vals = {
            'bank_account': partner_bank,

            'id': partner_bank.acc_number.replace(' ', ''),
        }

        if partner_bank.bank_id:
            vals['FinancialInstitutionBranch_vals'] = self._get_financial_institution_branch_vals(partner_bank.bank_id)

        return vals

    def _get_invoice_payment_means_vals_list(self, invoice):
        vals = {
            'payment_means_code': 30,
            'payment_due_date': invoice.invoice_date_due or invoice.invoice_date,
            'instruction_id': invoice.payment_reference,
            'payment_id_vals': [invoice.payment_reference or invoice.name],
        }

        if invoice.partner_bank_id:
            vals['PayeeFinancialAccount_vals'] = self._get_financial_account_vals(invoice.partner_bank_id)

        return [vals]

    def _get_tax_category_name_map(self):
        return {
            'S': _("Standard rate"),
            'E': _("Exempt from tax"),
            'Z': _("Zero rated goods"),
            'AE': _("VAT Reverse Charge"),
        }

    def _get_tax_category_list(self, taxes):
        """ See https://unece.org/fileadmin/DAM/trade/untdid/d16b/tred/tred5305.htm

        :param taxes:   account.tax records.
        :return:        A list of values to fill the TaxCategory foreach template.
        """
        tax_category_name_map = self._get_tax_category_name_map()

        mapping = {}

        for tax in taxes:
            if tax.amount == 0.0:
                category_code = 'Z'
            elif tax.amount < 0.0:
                category_code = 'AE'
            else:
                category_code = 'S'

            percent = tax.amount if tax.amount_type == 'percent' else False

            mapping_key = (category_code, percent)
            mapping.setdefault(mapping_key, {
                'id': category_code,
                'percent': percent,
            })

        return [{
            **x,
            'name': tax_category_name_map[x['id']],
            'TaxScheme_vals': {},
        } for x in mapping.values()]

    def _get_invoice_tax_totals_vals_list(self, invoice, taxes_vals):
        balance_sign = -1 if invoice.is_inbound() else 1

        return [{
            'currency': invoice.currency_id,
            'tax_amount': balance_sign * taxes_vals['tax_amount_currency'],
            'TaxSubtotal_vals': [{
                'currency': invoice.currency_id,
                'taxable_amount': balance_sign * vals['base_amount_currency'],
                'tax_amount': balance_sign * vals['tax_amount_currency'],
                'percent': vals['_tax_category_vals_']['percent'],
                'TaxCategory_vals': vals['_tax_category_vals_'],
            } for vals in taxes_vals['tax_details'].values()],
        }]

    def _get_invoice_line_item_vals(self, line, taxes_vals):
        """ Method used to fill the cac:InvoiceLine/cac:Item node.
        It provides information about what the product you are selling.

        :param line:        An invoice line.
        :param taxes_vals:  The tax details for the current invoice line.
        :return:            A python dictionary.

        """
        product = line.product_id
        taxes = line.tax_ids.flatten_taxes_hierarchy()
        tax_category_vals_list = self._get_tax_category_list(taxes)

        return {
            # Simple description about what you are selling.
            'description': line.name.replace('\n', ', '),

            # The name of the item.
            # TODO: same as description most of the time?
            'name': product.name,

            # Identifier of the product.
            # TODO: 'barcode' ?
            'SellersItemIdentification_vals': {'id': product.code},

            # The main tax applied. Only one is allowed.
            # TODO: eco-tax? recupel? *~*
            'ClassifiedTaxCategory_vals': tax_category_vals_list,
        }

    def _get_invoice_line_allowance_vals_list(self, line):
        """ Method used to fill the cac:InvoiceLine/cac:AllowanceCharge node.

        Allowances are distinguished from charges using the ChargeIndicator node with 'false' as value.

        :param line:    An invoice line.
        :return:        A list of python dictionaries.
        """
        if not line.discount:
            return []

        # Price subtotal without discount:
        net_price_subtotal = line.price_subtotal
        # Price subtotal with discount:
        gross_price_subtotal = line.currency_id.round(net_price_subtotal / (1.0 - (line.discount or 0.0) / 100.0))

        allowance_vals = {
            'currency': line.currency_id,

            # Must be 'false' since this method is for allowances.
            'charge_indicator': 'false',

            # A reason should be provided. In Odoo, we only manage discounts.
            # Full code list is available here:
            # https://docs.peppol.eu/poacc/billing/3.0/codelist/UNCL5189/
            'allowance_charge_reason_code': 95,

            # The discount should be provided as an amount.
            'amount': gross_price_subtotal - net_price_subtotal,
        }

        return [allowance_vals]

    def _get_invoice_line_price_vals(self, line):
        """ Method used to fill the cac:InvoiceLine/cac:Price node.
        It provides information about the price applied for the goods and services invoiced.

        :param line:    An invoice line.
        :return:        A python dictionary.
        """
        # Price subtotal without discount:
        net_price_subtotal = line.price_subtotal
        # Price subtotal with discount:
        gross_price_subtotal = net_price_subtotal / (1.0 - (line.discount or 0.0) / 100.0)
        # Price subtotal with discount / quantity:
        gross_price_unit = (gross_price_subtotal / line.quantity) if line.quantity else 0.0

        return {
            'currency': line.currency_id,

            # The price of an item, exclusive of VAT, after subtracting item price discount.
            'price_amount': gross_price_unit,

            # The number of item units to which the price applies.
            # In Odoo, this value is always 1 because the user always encodes the unit price of a product.
            'base_quantity': 1,
        }

    def _get_invoice_line_vals(self, line, taxes_vals):
        """ Method used to fill the cac:InvoiceLine node.
        It provides information about the invoice line.

        :param line:    An invoice line.
        :return:        A python dictionary.
        """
        allowance_charge_vals_list = self._get_invoice_line_allowance_vals_list(line)

        return {
            'currency': line.currency_id,

            # The requirement is the id has to be unique by invoice line.
            'id': line.id,

            'invoiced_quantity': line.quantity,
            'line_extension_amount': line.price_subtotal,

            'AllowanceCharge_vals': allowance_charge_vals_list,
            'TaxTotal_vals': self._get_invoice_tax_totals_vals_list(line.move_id, taxes_vals),
            'Item_vals': self._get_invoice_line_item_vals(line, taxes_vals),
            'Price_vals': self._get_invoice_line_price_vals(line),
        }

    def _export_invoice_vals(self, invoice):
        def grouping_key_generator(tax_values):
            tax = tax_values['tax_id']
            tax_category_vals = self._get_tax_category_list(tax)[0]
            return {
                'tax_category_id': tax_category_vals['id'],
                'tax_category_percent': tax_category_vals['percent'],
                '_tax_category_vals_': tax_category_vals,
            }

        # Compute the tax details for the whole invoice and each invoice line separately.
        taxes_vals = invoice._prepare_edi_tax_details(grouping_key_generator=grouping_key_generator)

        # Compute values for invoice lines.
        line_extension_amount = 0.0

        invoice_lines = invoice.invoice_line_ids.filtered(lambda line: not line.display_type)
        allowance_charge_vals_list = []
        invoice_line_vals_list = []
        for line in invoice_lines:
            line_taxes_vals = taxes_vals['invoice_line_tax_details'][line]
            line_vals = self._get_invoice_line_vals(line, line_taxes_vals)
            invoice_line_vals_list.append(line_vals)

            line_extension_amount += line_vals['line_extension_amount']

        # Compute the total allowance/charge amounts.
        allowance_total_amount = 0.0
        for allowance_charge_vals in allowance_charge_vals_list:
            if allowance_charge_vals['charge_indicator'] == 'false':
                allowance_total_amount += allowance_charge_vals['amount']

        supplier = invoice.company_id.partner_id.commercial_partner_id
        customer = invoice.commercial_partner_id

        vals = {
            'builder': self,
            'invoice': invoice,
            'supplier': supplier,
            'customer': customer,

            'taxes_vals': taxes_vals,

            'format_float': self.format_float,

            'PartyNameType_template': 'account_edi_ubl.ubl_20_PartyNameType',
            'CountryType_template': 'account_edi_ubl.ubl_20_CountryType',
            'AddressType_template': 'account_edi_ubl.ubl_20_AddressType',
            'TaxSchemeType_template': 'account_edi_ubl.ubl_20_TaxSchemeType',
            'PartyTaxSchemeType_template': 'account_edi_ubl.ubl_20_PartyTaxSchemeType',
            'PartyLegalEntityType_template': 'account_edi_ubl.ubl_20_PartyLegalEntityType',
            'ContactType_template': 'account_edi_ubl.ubl_20_ContactType',
            'PartyType_template': 'account_edi_ubl.ubl_20_PartyType',
            'PartyIdentificationType_template': 'account_edi_ubl.ubl_20_PartyIdentificationType',
            'SupplierPartyType_template': 'account_edi_ubl.ubl_20_SupplierPartyType',
            'CustomerPartyType_template': 'account_edi_ubl.ubl_20_CustomerPartyType',
            'FinancialInstitutionType_template': 'account_edi_ubl.ubl_20_FinancialInstitutionType',
            'BranchType_template': 'account_edi_ubl.ubl_20_BranchType',
            'FinancialAccountType_template': 'account_edi_ubl.ubl_20_FinancialAccountType',
            'PaymentMeansType_template': 'account_edi_ubl.ubl_20_PaymentMeansType',
            'PaymentTermsType_template': 'account_edi_ubl.ubl_20_PaymentTermsType',
            'TaxCategoryType_template': 'account_edi_ubl.ubl_20_TaxCategoryType',
            'TaxSubtotalType_template': 'account_edi_ubl.ubl_20_TaxSubtotalType',
            'TaxTotalType_template': 'account_edi_ubl.ubl_20_TaxTotalType',
            'MonetaryTotalType_template': 'account_edi_ubl.ubl_20_MonetaryTotalType',
            'ItemIdentificationType_template': 'account_edi_ubl.ubl_20_ItemIdentificationType',
            'ItemType_template': 'account_edi_ubl.ubl_20_ItemType',
            'AllowanceChargeType_template': 'account_edi_ubl.ubl_20_AllowanceChargeType',
            'PriceType_template': 'account_edi_ubl.ubl_20_PriceType',
            'InvoiceLineType_template': 'account_edi_ubl.ubl_20_InvoiceLineType',
            'InvoiceType_template': 'account_edi_ubl.ubl_20_InvoiceType',

            'vals': {

                'ubl_version': 2.0,
                'note_vals': [html2plaintext(invoice.narration)] if invoice.narration else [],
                'AccountingSupplierParty_vals': {
                    'Party_vals': self._get_partner_party_vals(supplier),
                },
                'AccountingCustomerParty_vals': {
                    'Party_vals': self._get_partner_party_vals(customer),
                },
                'PaymentMeans_vals': self._get_invoice_payment_means_vals_list(invoice),
                'PaymentTerms_vals': [{
                    'note_vals': [invoice.invoice_payment_term_id.name],
                }],
                'AllowanceCharge_vals': allowance_charge_vals_list,
                'TaxTotal_vals': self._get_invoice_tax_totals_vals_list(invoice, taxes_vals),
                'LegalMonetaryTotal_vals': {
                    'currency': invoice.currency_id,
                    'line_extension_amount': line_extension_amount,
                    'tax_exclusive_amount': invoice.amount_untaxed,
                    'tax_inclusive_amount': invoice.amount_total,
                    'allowance_total_amount': allowance_total_amount or None,
                    'prepaid_amount': invoice.amount_total - invoice.amount_residual,
                    'payable_amount': invoice.amount_residual,
                },
                'InvoiceLine_vals': invoice_line_vals_list,
            },
        }

        if invoice.move_type == 'out_invoice':
            vals['main_template'] = 'account_edi_ubl.ubl_20_Invoice'
        else:
            vals['main_template'] = 'account_edi_ubl.ubl_20_CreditNote'

        return vals

    def _export_invoice_constraints(self, invoice, vals):
        return {
            'ubl20_supplier_name_required': self._check_required_fields(vals['supplier'], 'name'),
            'ubl20_customer_name_required': self._check_required_fields(vals['customer'], 'name'),
            'ubl20_commercial_customer_name_required': self._check_required_fields(vals['customer'].commercial_partner_id, 'name'),
            'ubl20_invoice_name_required': self._check_required_fields(invoice, 'name'),
            'ubl20_invoice_date_required': self._check_required_fields(invoice, 'invoice_date'),
        }

    def _export_invoice(self, invoice):
        vals = self._export_invoice_vals(invoice)
        template = self.env.ref(vals['main_template'])
        errors = self._check_constraints(self._export_invoice_constraints(invoice, vals))
        return self.cleanup_xml_content(template._render(vals)), errors

    # -------------------------------------------------------------------------
    # IMPORT
    # -------------------------------------------------------------------------

    def _import_get_ubl_document_type(self, filename, tree):
        if tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}Invoice':
            return 'in_invoice'
        if tree.tag == '{urn:oasis:names:specification:ubl:schema:xsd:CreditNote-2}CreditNote':
            return 'in_refund'

    def _import_retrieve_partner_map(self, company):

        def with_vat(tree, extra_domain):
            vat_node = tree.find('.//{*}AccountingSupplierParty/{*}Party//{*}CompanyID')

            if vat_node is None:
                return None

            return self.env['res.partner'].search(extra_domain + [('vat', '=', vat_node.text)], limit=1)

        def with_phone_mail(tree, extra_domain):
            domains = []

            phone_node = tree.find(tree, './/{*}AccountingSupplierParty/{*}Party//{*}Telephone')
            if phone_node is not None:
                domains.append([('phone', '=', phone_node.text)])
                domains.append([('mobile', '=', phone_node.text)])

            mail_node = tree.find(tree, './/{*}AccountingSupplierParty/{*}Party//{*}ElectronicMail')
            if mail_node is not None:
                domains.append([('email', '=', mail_node.text)])

            if not domains:
                return None

            return self.env['res.partner'].search(extra_domain + expression.OR(domains), limit=1)

        def with_name(tree, extra_domain):
            name_node = tree.find('.//{*}AccountingSupplierParty/{*}Party//{*}Name')

            if name_node is None:
                return None

            return self.env['res.partner'].search(extra_domain + [('name', 'ilike', name_node.text)], limit=1)

        return {
            10: lambda tree: with_vat(tree, [('company_id', '=', company.id)]),
            20: lambda tree: with_vat(tree, []),
            30: lambda tree: with_phone_mail(tree, [('company_id', '=', company.id)]),
            40: lambda tree: with_phone_mail(tree, []),
            50: lambda tree: with_name(tree, [('company_id', '=', company.id)]),
            60: lambda tree: with_name(tree, []),
        }

    def _import_retrieve_product_map(self, company):

        def with_code_barcode(tree, extra_domain):
            domains = []

            default_code_node = tree.find('./{*}Item/{*}SellersItemIdentification/{*}ID')
            if default_code_node is not None:
                domains.append([('default_code', '=', default_code_node.text)])

            barcode_node = tree.find("./{*}Item/{*}StandardItemIdentification/{*}ID[@schemeID='0160']")
            if barcode_node is not None:
                domains.append([('barcode', '=', barcode_node.text)])

            if not domains:
                return None

            return self.env['product.product'].search(extra_domain + expression.OR(domains), limit=1)

        def with_name(tree, extra_domain):
            name_node = tree.find('./{*}Item/{*}Name')

            if name_node is None:
                return None

            return self.env['product.product'].search(extra_domain + [('name', 'ilike', name_node.text)], limit=1)

        return {
            10: lambda tree: with_code_barcode(tree, [('company_id', '=', company.id)]),
            20: lambda tree: with_code_barcode(tree, []),
            30: lambda tree: with_name(tree, [('company_id', '=', company.id)]),
            40: lambda tree: with_name(tree, []),
        }

    def _import_retrieve_info_from_map(self, tree, import_method_map):
        for key in sorted(import_method_map.keys()):
            record = import_method_map[key](tree)
            if record:
                return record

        return None

    # -------------------------------------------------------------------------
    # IMPORT: INVOICE
    # -------------------------------------------------------------------------

    def _import_fill_invoice_line_form(self, journal, tree, invoice_form, invoice_line_form):
        # ==== product_id ====

        product = self._import_retrieve_info_from_map(
            tree,
            self._import_retrieve_product_map(journal),
        )
        if product is not None:
            invoice_line_form.product_id = product

        # ==== quantity ====

        invoiced_quantity_tag = 'InvoicedQuantity' if invoice_form.move_type == 'in_invoice' else 'CreditedQuantity'
        quantity_node = tree.find('./{*}' + invoiced_quantity_tag)
        if quantity_node is not None:
            invoice_line_form.quantity = float(quantity_node.text)

        # ==== price_unit ====

        line_extension_amount_node = tree.find('./{*}LineExtensionAmount')
        price_unit_node = tree.find('./{*}Price/{*}PriceAmount')
        discount_node = tree.find('./{*}AllowanceCharge/{*}Amount')

        if line_extension_amount_node.text is None and price_unit_node is not None:
            net_price_subtotal = float(price_unit_node.text) * invoice_line_form.quantity
        elif line_extension_amount_node.text is not None:
            net_price_subtotal = float(line_extension_amount_node.text)

        if line_extension_amount_node.text is not None and invoice_line_form.quantity:
            if discount_node is not None:
                gross_price_subtotal = float(discount_node.text) + net_price_subtotal
                invoice_line_form.price_unit = gross_price_subtotal / invoice_line_form.quantity
                invoice_line_form.discount = (1 - (net_price_subtotal / gross_price_subtotal)) * 100.0
            else:
                invoice_line_form.price_unit = net_price_subtotal / invoice_line_form.quantity

        # ==== name ====

        name_node = tree.find('./{*}Item/{*}Description')
        if name_node is not None:
            invoice_line_form.name = name_node.text

        # ==== tax_ids ====

        taxes = []
        for tax_subtotal_el in tree.findall('./{*}TaxTotal/{*}TaxSubtotal'):
            taxable_amount_el = tax_subtotal_el.find('./{*}TaxableAmount')
            tax_amount_el = tax_subtotal_el.find('./{*}TaxAmount')

            # Process only subtotals having the same currency as the invoice.
            if taxable_amount_el.attrs.get('currencyID', '').upper() != invoice_form.currency_id.name.upper():
                continue
            if tax_amount_el.attrs.get('currencyID', '').upper() != invoice_form.currency_id.name.upper():
                continue

            tax_categ_id_el = tax_subtotal_el.find('./{*}TaxCategoryType/{*}ID')
            tax_categ_percent_el = tax_subtotal_el.find('./{*}TaxCategoryType/{*}Percent')

            if tax_categ_percent_el is not None:
                tax = self.env['account.tax'].search([
                    ('company_id', '=', journal.company_id.id),
                    ('amount', '=', float(tax_categ_percent_el.text)),
                    ('amount_type', '=', 'percent'),
                    ('type_tax_use', '=', 'sale'),
                ], limit=1)
                if tax:
                    taxes.append(tax)
            elif all(x is not None for x in (tax_categ_id_el, taxable_amount_el, tax_amount_el)):
                if tax_categ_id_el.text.upper() == 'S':
                    amount = float(tax_amount_el.text) / float(taxable_amount_el.text)
                elif tax_categ_id_el.text.upper() == 'Z':
                    amount = 0.0
                else:
                    continue

                tax = self.env['account.tax'].search([
                    ('company_id', '=', journal.company_id.id),
                    ('amount', '=', amount),
                    ('amount_type', '=', 'percent'),
                    ('type_tax_use', '=', 'sale'),
                ], limit=1)
                if tax:
                    taxes.append(tax)

        if not taxes:
            tax_categ_percent_el = tree.find('./{*}Item/{*}ClassifiedTaxCategory/{*}Percent')
            if tax_categ_percent_el is not None:
                tax = self.env['account.tax'].search([
                    ('company_id', '=', journal.company_id.id),
                    ('amount', '=', float(tax_categ_percent_el.text)),
                    ('amount_type', '=', 'percent'),
                    ('type_tax_use', '=', 'sale'),
                ], limit=1)
                if tax:
                    taxes.append(tax)

        invoice_line_form.tax_ids.clear()
        for tax in taxes:
            invoice_line_form.tax_ids.add(tax)

    def _import_fill_invoice_form(self, journal, tree, invoice_form):
        # ==== partner_id ====

        partner = self._import_retrieve_info_from_map(
            tree,
            self._import_retrieve_partner_map(journal),
        )
        if partner:
            invoice_form.partner_id = partner

        # Partner is a required field.
        if not invoice_form.partner_id:
            return None

        # ==== currency_id ====

        currency_code_node = tree.find('.//{*}DocumentCurrencyCode')
        if currency_code_node is not None:
            currency = self.env['res.currency'].with_context(active_test=False).search([
                ('name', '=', currency_code_node.text),
            ], limit=1)
            if currency:
                invoice_form.currency_id = currency

        # ==== ref ====

        ref_node = tree.find('./{*}ID')
        if ref_node is not None:
            invoice_form.ref = ref_node.text

        # ==== payment_reference ====

        payment_reference_node = tree.find('.//{*}InstructionID')
        if payment_reference_node is not None:
            invoice_form.payment_reference = payment_reference_node.text

        # ==== invoice_date ====

        invoice_date_node = tree.find('./{*}IssueDate')
        if invoice_date_node is not None:
            invoice_form.invoice_date = invoice_date_node.text

        # ==== invoice_date_due ====

        invoice_date_due_node = tree.find('.//{*}PaymentDueDate')
        if invoice_date_due_node is not None:
            invoice_form.invoice_date_due = invoice_date_due_node.text

        # ==== invoice_incoterm_id ====

        incoterm_code_node = tree.find('./{*}TransportExecutionTerms/{*}DeliveryTerms/{*}ID')
        if incoterm_code_node is not None:
            incoterm = self.env['account.incoterms'].search([('code', '=', incoterm_code_node.text)], limit=1)
            if incoterm:
                invoice_form.invoice_incoterm_id = incoterm

        # ==== invoice_line_ids ====

        invoice_line_tag = 'InvoiceLine' if invoice_form.move_type == 'in_invoice' else 'CreditNoteLine'
        for i, invl_el in enumerate(tree.findall('./{*}' + invoice_line_tag)):
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.sequence = i
                self._import_fill_invoice_line_form(journal, invl_el, invoice_form, invoice_line_form)

        invoice = invoice_form.save()

        # ==== Regenerate the PDF ====

        attachment_vals_list = []
        for doc_el in tree.findall('./{*}AdditionalDocumentReference'):
            attachment_name_node = doc_el.find('./{*}ID')
            attachment_data_node = doc_el.find('./{*}Attachment//{*}EmbeddedDocumentBinaryObject')
            if attachment_name_node is None or attachment_data_node is None:
                continue

            attachment_data = attachment_data_node.text

            # Fix incorrect padding.
            modulo = len(attachment_data_node.text) % 3
            if modulo:
                attachment_data += '=' * modulo

            # Normalize the name of the file : some e-fff emitters put the full path of the file
            # (Windows or Linux style) and/or the name of the xml instead of the pdf.
            # Get only the filename with a pdf extension.
            attachment_vals_list.append({
                'name': f"{PureWindowsPath(attachment_name_node.text).stem}.pdf",
                'res_id': invoice.id,
                'res_model': invoice._name,
                'datas': attachment_data,
                'type': 'binary',
                'mimetype': 'application/pdf',
            })

        if attachment_vals_list:
            attachments = self.env['ir.attachment'].create(attachment_vals_list)
            invoice.with_context(no_new_invoice=True).message_post(attachment_ids=attachments.ids)

        return invoice

    def _import_invoice(self, journal, filename, tree, existing_invoice=None):
        # Ensure both are matched.
        move_type = self._import_get_ubl_document_type(filename, tree)
        if not move_type or (existing_invoice and existing_invoice.move_type != move_type):
            return

        invoice = existing_invoice or self.env['account.move']
        invoice_form = Form(invoice.with_context(
            account_predictive_bills_disable_prediction=True,
            default_move_type=move_type,
            default_journal_id=journal.id,
        ))
        return self._import_fill_invoice_form(journal, tree, invoice_form)

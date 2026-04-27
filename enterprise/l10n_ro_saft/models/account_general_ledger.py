# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

import stdnum.ro

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.tools import float_repr, SQL, Query

from odoo.addons.account_edi_ubl_cii.models.account_edi_common import UOM_TO_UNECE_CODE


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options):
        super()._custom_options_initializer(report, options, previous_options)

        if self.env.company.account_fiscal_country_id.code != 'RO':
            return

        options.setdefault('buttons', []).append({
            'name': _('SAF-T (D406 Declaration)'),
            'sequence': 50,
            'action': 'export_file',
            'action_param': 'l10n_ro_export_saft_to_xml_monthly',
            'file_export_type': _('XML')
        })
        options.setdefault('buttons', []).append({
            'name': _('SAF-T (D406 Asset Declaration)'),
            'sequence': 51,
            'action': 'export_file',
            'action_param': 'l10n_ro_export_saft_to_xml_assets',
            'file_export_type': _('XML')
        })

    @api.model
    def l10n_ro_export_saft_to_xml_monthly(self, options):
        options['l10n_ro_saft_type'] = 'monthly'
        options['l10n_ro_saft_required_sections'] = self._set_l10n_ro_saft_required_sections(options['l10n_ro_saft_type'])
        return self.l10n_ro_export_saft_to_xml(options)

    @api.model
    def l10n_ro_export_saft_to_xml_assets(self, options):
        options['l10n_ro_saft_type'] = 'assets'
        options['l10n_ro_saft_required_sections'] = self._set_l10n_ro_saft_required_sections(options['l10n_ro_saft_type'])
        return self.l10n_ro_export_saft_to_xml(options)

    @api.model
    def _set_l10n_ro_saft_required_sections(self, export_type):
        """Define which sections of the XML are required to export based on the
        type of export, which can either be monthly, assets"""
        monthly = (export_type == 'monthly')
        assets = (export_type == 'assets')

        return {
            'master_files': {
                'general_ledger_accounts': monthly or assets,
                'customers': monthly,
                'suppliers': monthly,
                'tax_table': monthly,
                'uom_table': monthly,
                'analysis_type_table': monthly or assets,
                'movement_type_table': False,
                'products': monthly,
                'physical_stocks': False,
                'owners': False,
                'assets': assets,
            },
            'general_ledger_entries': monthly,
            'source_documents': {
                'sales_invoices': monthly,
                'purchase_invoices': monthly,
                'payments': monthly,
                'movement_of_goods': False,
                'asset_transactions': assets,
            }
        }

    @api.model
    def l10n_ro_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        values = self._l10n_ro_saft_prepare_report_values(report, options)
        file_data = report._generate_file_data_with_error_check(
            options,
            self.env['ir.qweb']._render,
            {'values': values, 'template': 'l10n_ro_saft.saft_template', 'file_type': 'xml'},
            values['errors'],
        )
        return file_data

    @api.model
    def _l10n_ro_saft_check_report_values(self, values, options):
        values['errors'] = {
            **self._l10n_ro_saft_check_header_values(options, values),
            **self._l10n_ro_saft_check_partner_values(values),
            **self._l10n_ro_saft_check_tax_values(options, values),
            **self._l10n_ro_saft_check_product_values(values),
            **self._l10n_ro_saft_check_asset_values(values),
        }

    @api.model
    def _l10n_ro_saft_prepare_report_values(self, report, options):
        options['saft_allow_empty_address'] = self.env.company.country_code == 'RO'
        values = super()._saft_prepare_report_values(report, options)

        # The saft template needs to know which sections are requested
        values['l10n_ro_saft_required_sections'] = options['l10n_ro_saft_required_sections']

        self._l10n_ro_saft_fill_header_values(options, values)
        self._l10n_ro_saft_fill_partner_values(values)
        self._l10n_ro_saft_fill_tax_values(options, values)
        self._l10n_ro_saft_fill_uom_values(options, values)
        self._l10n_ro_saft_fill_product_values(options, values)
        self._l10n_ro_saft_fill_account_code_by_id(values)
        self._l10n_ro_saft_fill_invoice_values(values)
        self._l10n_ro_saft_fill_payment_values(values)
        self._l10n_ro_saft_fill_report_assets_values(options, values)
        self._l10n_ro_saft_fill_asset_transactions_values(options, values)
        self._l10n_ro_saft_clean_customer_suppliers_vals_list(options, values)
        self._l10n_ro_saft_clean_move_vals_list(values)
        self._l10n_ro_saft_check_report_values(values, options)

        return values

    @api.model
    def _l10n_ro_saft_check_header_values(self, options, values):
        """ Check whether the company configuration is correct for filling in the Header. """
        def get_company_action(message):
            return {
                'message': message,
                'action_text': self.env._("View Company/ies"),
                'action': values['company']._get_records_action(name=self.env._('Invalid Company/ies'))
            }

        errors = {}

        # The company must have a Tax Accounting Basis defined.
        if not values['company'].l10n_ro_saft_tax_accounting_basis:
            errors['settings_accounting_basis_missing'] = {
                'message': _('Please set the company Tax Accounting Basis.'),
                'action_text': _('View Settings'),
                'action': {
                    'name': _("Settings"),
                    'type': 'ir.actions.act_url',
                    'target': 'self',
                    'url': '/odoo/settings#l10n_ro_saft_tax_accounting_basis',
                }
            }

        # The company must have a bank account defined.
        if not values['company'].bank_ids:
            errors['company_bank_account_missing'] = {
                'message': _('Please define a `Bank Account` for your company.'),
                'action_text': _('View Company/ies'),
                'action': values['company'].partner_id._get_records_action(name=_("Invalid Company/ies")),
            }

        # The company must have a telephone number defined.
        if not values['company'].partner_id.phone and not values['company'].partner_id.mobile:
            errors['company_phone_missing'] = get_company_action(_('Please define a `Telephone Number` for your company.'))

        # The company must either have a VAT number defined (if it is registered for VAT in Romania),
        # or have its CUI number in the company_registry field (if not registered for VAT).
        partner = values['company'].partner_id
        if not partner.vat:
            if partner.company_registry:
                if not stdnum.ro.cui.is_valid(partner.company_registry):
                    errors['company_registry_number_invalid'] = get_company_action(_('The CUI number for your company (under `Company Registry` in the Company settings) is incorrect.'))
            else:
                errors['company_vat_registry_number_missing'] = get_company_action(_('In the Company settings, please set your company VAT number under `Tax ID` if registered for VAT, or your CUI number under `Company Registry`.'))

        return errors

    @api.model
    def _l10n_ro_saft_fill_header_values(self, options, values):
        """ Fill in header values """
        # Mandatory values for the D.406 declaration
        values.update({
            'xmlns': 'mfp:anaf:dgti:d406:declaratie:v1',
            'file_version': '2.4.8',
        })

        # The TaxAccountingBasis should indicate the type of CoA that is installed.
        values.update({
            'accounting_basis': values['company'].l10n_ro_saft_tax_accounting_basis or 'A',
        })

        # The RegistrationNumber field for the company must be the VAT number if the
        # company is VAT-registered, otherwise, it should be the CUI number.
        partner = values['company'].partner_id
        if partner.vat:
            values['company_registration_number'] = stdnum.ro.cf.compact(partner.vat)
        elif partner.company_registry:
            values['company_registration_number'] = stdnum.ro.cui.compact(partner.company_registry)

        # The HeaderComment section must indicate the type of declaration:
        # - L for monthly returns
        # - T for quarterly returns
        # - A for annual returns
        # - C for returns on request (see l10n_ro_saft_stock/models/account_general_ledger.py)
        # - NL for non-residents monthly
        # - NT for non-residents quarterly
        if values['company'].country_code == 'RO':
            declaration_type = {
                'month': 'L',
                'quarter': 'T',
                'year': 'A',
                'fiscalyear': 'A',
            }.get(options['date']['period_type'], 'C')
        else:
            declaration_type = {
                'month': 'NL',
                'quarter': 'NT',
            }.get(options['date']['period_type'], '')
        values['declaration_type'] = declaration_type

    @api.model
    def _l10n_ro_saft_check_partner_values(self, values):
        """ Check whether all required information on partners is there. """
        def build_partners_action(partners, message):
            return {
                'message': message,
                'action': partners._get_records_action(name=self.env._("Invalid Partner(s)")),
            }

        faulty_partners = defaultdict(lambda: self.env['res.partner'])
        for partner_vals in values['partner_detail_map'].values():
            partner = partner_vals['partner']
            partner_type = partner_vals.get('type')
            if not partner.name:
                faulty_partners['partner_missing_name'] |= partner
            # Partner addresses must include the City and Country.
            if not partner.city:
                faulty_partners['partner_city_missing'] |= partner
            if not partner.country_code:
                faulty_partners['partner_country_missing'] |= partner
            # Partner country code should match the VAT prefix, if the VAT number is provided
            elif (
                partner_type in ('supplier', 'customer')
                and partner.vat
                and partner.vat[:2].isalpha()
                and partner.country_code.lower() != partner._split_vat(partner.vat)[0]
            ):
                faulty_partners['partner_vat_doesnt_match_country'] |= partner
            # Romanian company partners should have their VAT number or CUI number set in the Tax ID or company_registry field.
            # Foreign company partners should have their VAT number set in the Tax ID field.
            if partner_type in ('supplier', 'customer') and partner.is_company:
                if not partner.vat:
                    vat_country, vat_number = 'ro', ''
                elif not partner.vat[:2].isalpha():
                    vat_country, vat_number = 'ro', partner.vat
                else:
                    vat_country, vat_number = partner._split_vat(partner.vat)
                if partner.country_code == 'RO' or not partner.country_code:
                    cui = partner.company_registry or vat_number
                    if not stdnum.ro.cui.is_valid(cui):
                        faulty_partners['partner_registry_incorrect'] |= partner
                elif not partner.vat or not partner.simple_vat_check(vat_country, vat_number):
                    faulty_partners['partner_vat_incorrect'] |= partner
                elif partner.perform_vies_validation and not partner.vies_valid:
                    faulty_partners['partner_vies_failed'] |= partner

        descriptions = {
            "partner_city_missing": (_("Partners should have their city."), "warning"),
            "partner_country_missing": (_("Partners should have a country"), "warning"),
            "partner_vat_doesnt_match_country": (_("Partners' VAT prefix should correspond to their country."), "warning"),
            "partner_registry_incorrect": (_("Some partners have missing or invalid CUI numbers in `Company Registry`. Example of a valid CUI: 18547290"), "warning"),
            "partner_vat_missing": (_("Some partners have missing VAT numbers."), "warning"),
            "partner_vat_incorrect": (_("Some partners have invalid VAT numbers. Example of a valid VAT: RO18547290"), "warning"),
            "partner_vies_failed": (_('The VAT numbers for the following partners failed the VIES check:'), "warning"),
            "partner_missing_name": (_('These partners are missing a name:'), "danger"),
        }
        return {
            key: {
                'message': descriptions[key][0],
                'action_text': self.env._('View Partners'),
                'action': partners._get_records_action(name=self.env._("Invalid Partner(s)")),
                'level': descriptions[key][1]
            }
            for key, partners in faulty_partners.items()
        }

    @api.model
    def _l10n_ro_saft_get_registration_number(self, partner):
        """ Compute the RegistrationNumber field for a partner, consisting of a two-digit type followed by the partner's ID:
        00 + CUI number (without the 'RO' prefix), for economic operators registered in Romania;
        01 + country code + VAT code, for economic operators from EU Member States other than Romania;
        02 + country code + VAT code, for economic operators from non-EU states EU;
        03 + CNP, for Romanian citizens and individuals resident in Romania, or 03 + NIF for non-resident individuals;
        04 + partner ID, for customers from Romania not subject to VAT and whose CNP is unknown (e.g. e-commerce);
        05 + country code + partner ID, for customers from EU Member States other than Romania not subject to VAT;
        06 + country code + partner ID, for customers from non-EU states not subject to VAT;
        08 + 13 zeros (080000000000000), for unidentified customers in PoS transactions. This code is restricted ONLY to such transactions;
        09 + NIF for non-resident legal entities registered in Romania;
        (types 10 and 11 are restricted to banks)
        This function requires the country_code to be correctly set on the partner.

        :param partner: the res.partner for which to generate the registration number

        :return: the RegistrationNumber (a string)
        """
        if not partner:
            return '0'
        if partner.is_company:
            if not partner.vat:
                vat_country, vat_number = 'ro', ''
            elif not partner.vat[:2].isalpha():
                vat_country, vat_number = 'ro', partner.vat
            else:
                vat_country, vat_number = partner._split_vat(partner.vat)
            if partner.country_code == 'RO' or not partner.country_code:
                # For Romanian companies, the company_registry field should contain the CUI number, which is a 8-digit number without the 'RO' prefix
                # Alternatively, we can get the CUI from the VAT number by removing the 'RO' prefix.
                cui = partner.company_registry or vat_number
                return '00' + stdnum.ro.cui.compact(cui)
            elif partner.country_id in partner.env.ref('base.europe').country_ids:
                return '01' + vat_country.upper() + vat_number
            else:
                return '02' + vat_country.upper() + vat_number
        else:
            if partner.company_registry and stdnum.ro.cnp.is_valid(partner.company_registry):
                # For individuals having a valid CNP or NIF, that should be used
                return stdnum.ro.cnp.compact(partner.company_registry)
            elif partner.country_code == 'RO' or not partner.country_code:
                return '04' + str(partner.id)
            elif partner.country_id in partner.env.ref('base.europe').country_ids:
                return '05' + partner.country_code + str(partner.id)
            else:
                return '06' + partner.country_code + str(partner.id)
            # Code 08 (unidentified customer in PoS transactions) not implemented because the PoS does
            # not generate anonymous invoices.

    @api.model
    def _l10n_ro_saft_fill_partner_values(self, values):
        """ Fill in partner-related values in the values dict, performing checks as we go. """
        for partner_vals in values['partner_detail_map'].values():
            partner_vals['registration_number'] = self._l10n_ro_saft_get_registration_number(partner_vals['partner'])
            partner_vals['l10n_ro_saft_contacts'] = partner_vals['contacts'].filtered(
                # Only provide partners which have a first name, last name and phone number.
                lambda contact: ' ' in contact.name[1:-1] and (contact.phone or contact.mobile)
            )

    @api.model
    def _l10n_ro_saft_check_tax_values(self, options, values):
        """ Check whether all taxes have a Romanian SAFT tax type and tax code on them. """

        errors = {}
        if not options['l10n_ro_saft_required_sections']['master_files']['tax_table']:
            return errors

        encountered_tax_ids = [tax_vals['id'] for tax_vals in values['tax_vals_list']]
        faulty_taxes = self.env['account.tax'].search([
            ('id', 'in', encountered_tax_ids),
            '|', ('l10n_ro_saft_tax_type_id', '=', False), ('l10n_ro_saft_tax_code', '=', False)
        ])
        if faulty_taxes:
            errors['taxes_tax_type_missing'] = {
                'message': _('Some taxes are missing the "Romanian SAF-T Tax Type" '
                             'and/or "Romanian SAF-T Tax Code" field(s).'),
                'action_text': _('View Taxes'),
                'action': faulty_taxes._get_records_action(name=_("Taxes missing Tax Type or Tax Code (RO)")),
            }
        return errors

    @api.model
    def _l10n_ro_saft_fill_tax_values(self, options, values):
        """ Fill in the Romanian tax type, tax type description (in Romanian, if available), and tax code. """

        if not options['l10n_ro_saft_required_sections']['master_files']['tax_table']:
            return

        encountered_tax_ids = [tax_vals['id'] for tax_vals in values['tax_vals_list']]
        lang = self.env['res.lang']._get_code('ro_RO')
        encountered_taxes = self.env['account.tax'].with_context({'lang': lang}).browse(encountered_tax_ids)
        tax_fields_by_id = {
            tax.id: {
                'l10n_ro_saft_tax_type': tax.l10n_ro_saft_tax_type_id.code if tax.l10n_ro_saft_tax_type_id else '',
                'l10n_ro_saft_tax_type_description': tax.l10n_ro_saft_tax_type_id.description if tax.l10n_ro_saft_tax_type_id else '',
                'l10n_ro_saft_tax_code': tax.l10n_ro_saft_tax_code or '',
            }
            for tax in encountered_taxes
        }

        for line_vals in values['tax_detail_per_line_map'].values():
            for tax_detail_vals in line_vals['tax_detail_vals_list']:
                tax_fields = tax_fields_by_id[tax_detail_vals['tax_id']]
                tax_detail_vals.update(tax_fields)

        for tax_vals in values['tax_vals_list']:
            tax_fields = tax_fields_by_id[tax_vals['id']]
            tax_vals.update(tax_fields)

    def _get_encountered_product_uom_ids(self, values):
        return {
            line_vals['product_uom_id']
            for move_vals in values['move_vals_list']
            for line_vals in move_vals['line_vals_list']
            if line_vals['product_uom_id']
        }

    @api.model
    def _l10n_ro_saft_fill_uom_values(self, options, values):
        """ Fill UoMs and unece_code_by_uom """

        if not options['l10n_ro_saft_required_sections']['master_files']['uom_table']:
            values.update({
                'uoms': [],
                'unece_code_by_uom': {},
            })
            return

        encountered_product_uom_ids = sorted(self._get_encountered_product_uom_ids(values))
        uoms = self.env['uom.uom'].browse(encountered_product_uom_ids)
        non_ref_uoms = uoms.filtered(lambda uom: uom.uom_type != 'reference')
        if non_ref_uoms:
            # search base UoM for UoM master table
            uoms |= self.env['uom.uom'].search([('category_id', 'in', non_ref_uoms.category_id.ids), ('uom_type', '=', 'reference')])

        # Provide a dict that links each UOM id to its UNECE code
        uom_xmlids = uoms.get_external_id()
        unece_code_by_uom = {
            uom.id: UOM_TO_UNECE_CODE.get(uom_xmlids[uom.id], 'C62') for uom in uoms
        }

        values.update({
            'uoms': uoms,
            'unece_code_by_uom': unece_code_by_uom,
        })

    @api.model
    def _l10n_ro_saft_check_product_values(self, values):
        """ Check whether each product has a ref, no products have duplicate refs,
            and if the intrastat module is installed, that each product has an Intrastat Code. """
        def get_product_action(message, products, level='warning'):
            return {
                'message': message,
                'action_text': self.env._('View Product(s)'),
                'action': products._get_records_action(name=self.env._("Invalid Product(s)")),
                'level': level,
            }

        encountered_product_ids = sorted(self._get_encountered_product_ids(values))
        encountered_products = self.env['product.product'].browse(encountered_product_ids)
        product_refs = encountered_products.mapped('default_code')
        products_no_ref = encountered_products.filtered(lambda product: not product.default_code)
        products_dup_ref = (encountered_products - products_no_ref).filtered(lambda product: product_refs.count(product.default_code) >= 2)

        errors = {}
        if products_no_ref:
            errors['product_internal_reference_missing'] = get_product_action(
                _('Some products have no `Internal Reference`.'),
                products_no_ref,
                level='danger'
            )
        if products_dup_ref:
            errors['product_internal_reference_duplicated'] = get_product_action(
                _('Some products have duplicated `Internal Reference`, please make them unique.'),
                products_dup_ref,
                level='danger'
            )
        if 'intrastat_code_id' not in encountered_products:  # intrastat module isn't installed, don't check for the instrastat code
            return errors

        products_without_intrastat_code = encountered_products.filtered(lambda p: p.type != 'service' and not p.intrastat_code_id)
        if products_without_intrastat_code:
            errors['product_intrastat_code_missing'] = get_product_action(
                _("The Intrastat code isn't set on some products."),
                products_without_intrastat_code
            )

        return errors

    def _get_commodity_code(self, product):
        if product.type == 'service':
            return '00000000'
        else:
            return product.intrastat_code_id.code if 'intrastat_code_id' in product and product.intrastat_code_id else '0'

    def _get_encountered_product_ids(self, values):
        return {
            line_vals['product_id']
            for move_vals in values['move_vals_list']
            for line_vals in move_vals['line_vals_list']
            if line_vals['product_id']
        }

    @api.model
    def _l10n_ro_saft_fill_product_values(self, options, values):
        """ Fill product_vals_list """
        if not options['l10n_ro_saft_required_sections']['master_files']['products']:
            values['product_vals_list'] = []
            return

        encountered_product_ids = sorted(self._get_encountered_product_ids(values))
        encountered_products = self.env['product.product'].browse(encountered_product_ids)
        product_vals_list = [
            {
                'id': product.id,
                'name': product.name,
                'default_code': product.default_code,
                'uom_id': product.uom_id.id,
                'product_category': product.product_tmpl_id.categ_id.name,
                # The account_intrastat module is not a dependency, so this code should work regardless of whether it is installed.
                'commodity_code': self._get_commodity_code(product),
            }
            for product in encountered_products
        ]
        values['product_vals_list'] = product_vals_list

    @api.model
    def _l10n_ro_saft_fill_account_code_by_id(self, values):
        """ Provide a mapping from account id to account code. We will need it when filling in
            the general ledger and the source documents, because the Romanian authorities want
            the account code not the account ID."""

        account_code_by_id = {
            account_vals['account'].id: account_vals['account'].code
            for account_vals in values['account_vals_list']
        }
        values['account_code_by_id'] = account_code_by_id

    @api.model
    def _l10n_ro_saft_fill_invoice_values(self, values):
        sale_invoice_vals = {
            'total_debit': 0.0,
            'total_credit': 0.0,
            'number': 0,
            'move_vals_list': [],
        }
        purchase_invoice_vals = {
            'total_debit': 0.0,
            'total_credit': 0.0,
            'number': 0,
            'move_vals_list': [],
        }

        self_invoices = self.env['account.move'].search([('l10n_ro_is_self_invoice', '=', True)])

        for move_vals in values['move_vals_list']:
            if move_vals['type'] not in {'out_invoice', 'out_refund', 'in_invoice', 'in_refund'}:
                continue

            # The invoice type is 380 for invoices, 381 for credit notes, 389 for self-invoices.
            # (these codes were selected from European Norm SIST EN-16931)
            if move_vals['id'] in self_invoices._ids:
                l10n_ro_saft_invoice_type = '389'
                l10n_ro_saft_self_billing_indicator = '389'
            else:
                l10n_ro_saft_invoice_type = '380' if move_vals['type'] in {'out_invoice', 'in_invoice'} else '381'
                l10n_ro_saft_self_billing_indicator = '0'

            move_vals.update({
                'invoice_line_vals_list': [],
                'l10n_ro_saft_invoice_type': l10n_ro_saft_invoice_type,
                'l10n_ro_saft_self_billing_indicator': l10n_ro_saft_self_billing_indicator
            })

            dict_to_update = sale_invoice_vals if move_vals['type'] in {'out_invoice', 'out_refund'} else purchase_invoice_vals
            for line_vals in move_vals['line_vals_list']:
                if not line_vals['account_type'] in ('asset_receivable', 'liability_payable') and line_vals['display_type'] == 'product':
                    dict_to_update['total_debit'] += line_vals['debit']
                    dict_to_update['total_credit'] += line_vals['credit']
                    move_vals['invoice_line_vals_list'].append(line_vals)

            dict_to_update['number'] += 1
            dict_to_update['move_vals_list'].append(move_vals)

        values.update({
            'sale_invoice_vals': sale_invoice_vals,
            'purchase_invoice_vals': purchase_invoice_vals,
        })

    @api.model
    def _l10n_ro_saft_fill_payment_values(self, values):
        payment_vals = {
            'total_debit': 0.0,
            'total_credit': 0.0,
            'number': 0,
            'move_vals_list': []
        }
        for move_vals in values['move_vals_list']:
            if not move_vals['statement_line_id']:
                continue
            move_vals.update({
                # Payment method '01' corresponds to cash, '03' corresponds to non-cash money transfers.
                'payment_method': '01' if move_vals['journal_type'] == 'cash' else '03',
                'description': move_vals['line_vals_list'][0]['name'],
                'payment_line_vals_list': [],
            })

            for line_vals in move_vals['line_vals_list']:
                if line_vals['account_type'] in ('asset_cash', 'liability_credit_card'):
                    move_vals['payment_line_vals_list'].append(line_vals)
                    payment_vals['total_debit'] += line_vals['debit']
                    payment_vals['total_credit'] += line_vals['credit']

            payment_vals['number'] += 1
            payment_vals['move_vals_list'].append(move_vals)

        values['payment_vals'] = payment_vals

    def _saft_get_account_type(self, account_type):
        # EXTENDS account_saft/models/account_general_ledger.py
        if self.env.company.account_fiscal_country_id.code != 'RO':
            return super()._saft_get_account_type(account_type)

        activ_types = ['asset_non_current', 'asset_fixed', 'asset_receivable', 'asset_cash', 'asset_current', 'asset_prepayments']
        pasiv_types = ['equity', 'equity_unaffected', 'liability_payable', 'liability_credit_card', 'liability_current', 'liability_non_current']

        if account_type in activ_types:
            return 'Activ'
        elif account_type in pasiv_types:
            return 'Pasiv'
        else:  # Fallback on bifunctional if it's anything else.
            return 'Bifunctional'

    # ####################################################
    # SAF-T ASSETS DECLARATION
    ####################################################

    @api.model
    def _l10n_ro_saft_float_repr(self, amount):
        # add 0. in case amount is -0.0 to make it positive
        return float_repr(amount + 0., self.env.company.currency_id.decimal_places)

    def _l10n_ro_saft_query_assets_values(self, options):

        query = Query(self.env, alias='asset', table=SQL.identifier('account_asset'))
        query.add_join('LEFT JOIN', alias='account', table='account_account', condition=SQL('asset.account_asset_id = account.id'))
        account_code = self.env['account.account']._field_to_sql('account', 'code', query)

        query = SQL(
            '''
            SELECT
                asset.id AS asset_id,
                asset.parent_id AS parent_id,
                asset.name AS asset_name,
                asset.original_value AS asset_original_value,
                COALESCE(asset.salvage_value, 0) AS asset_salvage_value,
                asset.disposal_date AS asset_disposal_date,
                asset.acquisition_date AS asset_acquisition_date,
                MIN(move.date) AS asset_date,
                COALESCE(MIN(original_bill_aml.invoice_date), asset.acquisition_date) AS asset_purchase_date,
                asset.state AS asset_state,
                asset.method_period AS asset_method_period,
                asset.method_number AS asset_method_number,
                asset.method AS asset_method,
                asset.method_progress_factor AS asset_method_progress_factor,
                asset.currency_id AS asset_currency_id,
                asset_category.code AS asset_category_code,
                %(account_code)s AS account_code,
                array_remove(array_agg(distinct partner.id), NULL) AS supplier_ids,
                COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date < %(date_from)s), 0) + COALESCE(asset.already_depreciated_amount_import, 0) AS depreciated_before,
                COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s), 0) AS depreciated_during,
                COALESCE(SUM(move.depreciation_value) FILTER (WHERE move.date BETWEEN %(date_from)s AND %(date_to)s AND move.asset_number_days IS NULL), 0) AS asset_disposal_value
            FROM %(from_clause)s
            LEFT JOIN account_move move ON move.asset_id = asset.id  AND move.state = 'posted'
            LEFT JOIN asset_move_line_rel rel ON rel.asset_id = asset.id
            LEFT JOIN account_move_line original_bill_aml ON original_bill_aml.id = rel.line_id
            LEFT JOIN res_partner partner ON partner.id = original_bill_aml.partner_id
            LEFT JOIN l10n_ro_saft_account_asset_category asset_category ON asset_category.id = asset.l10n_ro_saft_account_asset_category_id
            WHERE asset.company_id = %(company_id)s
              AND (asset.acquisition_date <= %(date_to)s OR move.date <= %(date_to)s)
              AND (asset.disposal_date >= %(date_from)s OR asset.disposal_date IS NULL)
              AND asset.state not in ('model', 'draft', 'cancelled')
              AND asset.active = 't'
            GROUP BY asset.id, account.id, asset_category.id, account_code
            ORDER BY account_code, asset.acquisition_date, asset.id;
            ''',
            account_code=account_code,
            date_from=options['date']['date_from'],
            date_to=options['date']['date_to'],
            from_clause=query.from_clause,
            company_id=self.env.company.id,
        )
        return query

    @api.model
    def _l10n_ro_saft_fill_report_assets_values(self, options, values):
        res = {
            'assets': [],
            'asset_partners': {},
        }

        if not options['l10n_ro_saft_required_sections']['master_files']['assets']:
            values.update(res)
            return

        if self.env.company.currency_id.name != 'RON':
            raise UserError(_('The SAF-T Asset Declaration cannot be generated if the currency of the company is not RON'))

        query = self._l10n_ro_saft_query_assets_values(options)
        self._cr.execute(query)
        asset_lines = self._cr.dictfetchall()

        # Assign the gross increases sub assets to their main asset (parent)
        parent_lines = []
        children_lines = defaultdict(list)
        for asset_line in asset_lines:
            if asset_line['parent_id']:
                children_lines[asset_line['parent_id']] += [asset_line]
            else:
                parent_lines += [asset_line]

        for asset in parent_lines:
            asset_children_lines = children_lines[asset['asset_id']]
            asset_val = self.env['account.asset.report.handler']._get_parent_asset_values(options, asset, asset_children_lines)

            depreciation_percentage = 0
            if asset['asset_method'] == 'linear':
                depreciation_percentage = round(1 / (asset['asset_method_number']), 2)
            elif asset['asset_method'] in ('degressive', 'degressive_then_linear'):
                depreciation_percentage = round(asset['method_progress_factor'] / asset['method_period'], 2)

            asset_method = {
                'linear': 'LINIARĂ',
                'degressive': 'DEGRESIVĂ',
                'degressive_then_linear': 'ACCELERATĂ'
            }.get(asset['asset_method'], '')

            # supplier id is the company if no supplier provided (self produced asset for example)
            asset['supplier_ids'] = asset['supplier_ids'] or [self.env.company.partner_id.id]

            asset['valuations'] = []
            valuation_data = {
                'asset_valuation_type': 'contabil',  # Accounting
                'valuation_class': asset['asset_category_code'],
                'acquisition_costs_begin': self._l10n_ro_saft_float_repr(asset_val['assets_date_from']),
                'acquisition_costs_end': self._l10n_ro_saft_float_repr(asset_val['assets_date_to']),
                'investment_support': self._l10n_ro_saft_float_repr(asset_val['assets_date_from'] - asset['asset_original_value'] + asset_val['assets_plus']),
                'asset_method_period': asset['asset_method_period'],
                'asset_method_number': asset['asset_method_number'],
                'asset_addition': self._l10n_ro_saft_float_repr(asset_val['assets_plus']),
                'transfers': self._l10n_ro_saft_float_repr(asset_val['assets_plus'] - asset_val['assets_minus']),
                'asset_disposal': self._l10n_ro_saft_float_repr(-asset_val['asset_disposal_value']),
                'book_value_begin': self._l10n_ro_saft_float_repr(asset_val['assets_date_from'] - asset_val['depre_date_from']),
                'depreciation_method': asset_method,
                'depreciation_percentage': self._l10n_ro_saft_float_repr(depreciation_percentage),
                'depreciation_for_period': self._l10n_ro_saft_float_repr(-asset_val['depre_plus']),
                'appreciation_for_period': self._l10n_ro_saft_float_repr(asset_val['depre_minus']),
                'accumulated_depreciation': self._l10n_ro_saft_float_repr(-asset_val['depre_date_to']),
                'book_value_end': self._l10n_ro_saft_float_repr(asset_val['assets_date_to'] - asset_val['depre_date_to']),
                'extraordinary_depreciation': [{
                    'method': 'NULL',
                    'amount_for_period': '0.00',
                }],
            }
            # the valuations tag can contain multiple valuation according to the documentation. However, when
            # reading more concisely the FAQ and reading more about this section, it seems that only one valuation
            # per asset is possible for Romania. The Romanian SAF-T template is therefore pre-adapted to be able to
            # handle a list of valuation elements, even though the list contain only a single element so far
            asset['valuations'].append(valuation_data)

            res['assets'].append(asset)
            res['asset_partners'][asset['asset_id']] = asset['supplier_ids']

        values.update(res)

    @api.model
    def _l10n_ro_saft_check_asset_values(self, values):
        """ Check whether assets have an asset_category or not"""
        errors = {}
        assets_without_category_ids = self.env['account.asset'].browse(
            [asset['asset_id'] for asset in values['assets'] if not asset['asset_category_code']]
        )
        if assets_without_category_ids:
            errors['missing_account_asset_category'] = {
                'message': _('Missing category on assets'),
                'action_text': _('Set asset categories'),
                'action': assets_without_category_ids._get_records_action(
                    name=_('Products with no commodity code'),
                    views=[
                        (self.env.ref('l10n_ro_saft.account_asset_missing_l10n_ro_saft_account_asset_category').id, 'list'),
                        (False, 'form')
                    ],
                    context={**self.env.context, 'create': False, 'delete': False, 'expand': True},
                ),
            }
        return errors

    @api.model
    def _l10n_ro_saft_query_asset_transactions_values(self, options):
        query = SQL(
            '''
            SELECT *
            FROM (
                -- Purchase and positive revaluation transactions
                -- are retrieved from the asset_move_line_rel table
                SELECT
                    move.id AS move_id,
                    move.name AS move_name,
                    move.date AS move_date,
                    move.asset_move_type AS asset_move_type,
                    move.depreciation_value AS depreciation_value,
                    aml.balance AS purchase_increase_amount,
                    COALESCE(asset.parent_id, asset.id) AS asset_id,
                    asset.original_value AS asset_original_value,
                    asset.net_gain_on_sale AS asset_net_gain_on_sale
                FROM account_move move
                LEFT JOIN account_move_line aml ON move.id = aml.move_id
                INNER JOIN asset_move_line_rel rel ON aml.id = rel.line_id
                INNER JOIN account_asset asset ON rel.asset_id = asset.id
                WHERE move.state = 'posted'
                  AND move.date BETWEEN %(date_from)s AND %(date_to)s
                  AND move.company_id = %(company_id)s
                  AND asset.state not in ('model', 'draft', 'cancelled')
                  AND asset.active = 't'
                UNION ALL
                -- Depreciations, negative revaluation, disposal, and sale transactions
                -- are retrieved from the asset_id field on account_move
                SELECT
                    move.id AS move_id,
                    move.name AS move_name,
                    move.date AS move_date,
                    move.asset_move_type AS asset_move_type,
                    move.depreciation_value AS depreciation_value,
                    0 AS purchase_increase_amount,
                    COALESCE(asset.parent_id, asset.id) AS asset_id,
                    asset.original_value AS asset_original_value,
                    asset.net_gain_on_sale AS asset_net_gain_on_sale
                FROM account_move move
                INNER JOIN account_asset asset ON move.asset_id = asset.id
                WHERE move.state = 'posted'
                  AND move.date BETWEEN %(date_from)s AND %(date_to)s
                  AND move.company_id = %(company_id)s
                  AND asset.state not in ('model', 'draft', 'cancelled')
                  AND asset.active = 't'
            ) asset_transactions
            ORDER BY asset_id, move_date, asset_move_type, move_name
            ''',
            date_from=options['date']['date_from'],
            date_to=options['date']['date_to'],
            company_id=self.env.company.id,
        )
        return query

    def _l10n_ro_saft_fill_asset_transactions_values(self, options, values):

        res = {
            'asset_transactions': [],
        }

        if not options['l10n_ro_saft_required_sections']['source_documents']['asset_transactions']:
            values.update(res)
            return

        asset_transaction_type = {
            'purchase': 10,
            'sale': 20,
            'depreciation': 30,
            'disposal': 50,
            'negative_revaluation': 60,
            'positive_revaluation': 70,
        }

        query = self._l10n_ro_saft_query_asset_transactions_values(options)
        self._cr.execute(query)
        for transaction in self._cr.dictfetchall():
            transaction['asset_transaction_id'] = transaction['move_id']
            transaction['asset_transaction_type'] = asset_transaction_type.get(transaction['asset_move_type'], 130)
            transaction['description'] = transaction['move_name']
            transaction['asset_transaction_date'] = transaction['move_date']
            transaction['depreciation_value'] *= (-1)  # must be provided with the opposite sign, so negative value in case of regular depreciation
            transaction['transaction_id'] = transaction['move_id']
            transaction['supplier_ids'] = values['asset_partners'].get(transaction['asset_id'], [self.env.company.partner_id.id])

            asset_transaction_valuation = {
                'asset_valuation_type': 'contabil',  # Accounting
                'acquisition_and_production_costs_on_transaction': (
                    self._l10n_ro_saft_float_repr(transaction['asset_original_value'])
                    if transaction['asset_move_type'] in ('purchase', 'positive_revaluation')
                    else "0.00"
                ),
                'book_value_transaction': self._l10n_ro_saft_float_repr(transaction['purchase_increase_amount'] or transaction['depreciation_value']),
                'asset_transaction_amount': (
                    self._l10n_ro_saft_float_repr(-transaction['asset_net_gain_on_sale'])
                    if transaction['asset_move_type'] == 'sale'
                    else self._l10n_ro_saft_float_repr(transaction['purchase_increase_amount'] or transaction['depreciation_value'])
                ),
            }

            transaction['asset_transaction_valuation'] = [asset_transaction_valuation]
            res['asset_transactions'].append(transaction)

        res['asset_transactions_number'] = len(res['asset_transactions'])

        values.update(res)

    @api.model
    def _l10n_ro_saft_clean_customer_suppliers_vals_list(self, options, values):
        if not options['l10n_ro_saft_required_sections']['master_files']['customers']:
            values['customer_vals_list'] = []

        if not options['l10n_ro_saft_required_sections']['master_files']['suppliers']:
            values['supplier_vals_list'] = []

    def _l10n_ro_saft_clean_move_vals_list(self, values):
        for journal_vals in values['journal_vals_list']:
            for move_vals in journal_vals['move_vals_list']:
                move_vals['line_vals_list'] = [vals for vals in move_vals['line_vals_list'] if vals['balance']]
            journal_vals['move_vals_list'] = [vals for vals in journal_vals['move_vals_list'] if vals['line_vals_list']]

        for move_vals in values['move_vals_list']:
            move_vals['line_vals_list'] = [vals for vals in move_vals['line_vals_list'] if vals['balance']]
        values['move_vals_list'] = [vals for vals in values['move_vals_list'] if vals['line_vals_list']]

    @api.model
    def _saft_fill_report_tax_details_values(self, report, options, values):
        # no need to compute this section if not required (for example in the asset saf-t report)
        if options.get('l10n_ro_saft_required_sections') and not options['l10n_ro_saft_required_sections']['master_files']['tax_table']:
            values['tax_vals_list'] = []
        else:
            super()._saft_fill_report_tax_details_values(report, options, values)

    @api.model
    def _saft_fill_report_general_ledger_entries(self, report, options, values):
        if options.get('l10n_ro_saft_required_sections') and not options['l10n_ro_saft_required_sections']['general_ledger_entries']:
            res = {
                'total_debit_in_period': 0.0,
                'total_credit_in_period': 0.0,
                'journal_vals_list': [],
                'move_vals_list': [],
                'tax_detail_per_line_map': {},
            }
            values.update(res)
        else:
            super()._saft_fill_report_general_ledger_entries(report, options, values)

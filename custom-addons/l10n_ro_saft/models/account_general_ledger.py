# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from collections import defaultdict

import stdnum.ro

from odoo import api, models, _
from odoo.addons.account_edi_ubl_cii.models.account_edi_common import UOM_TO_UNECE_CODE


class GeneralLedgerCustomHandler(models.AbstractModel):
    _inherit = 'account.general.ledger.report.handler'

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options)
        if self.env.company.account_fiscal_country_id.code == 'RO':
            options.setdefault('buttons', []).append({
                'name': _('SAF-T'),
                'sequence': 50,
                'action': 'export_file',
                'action_param': 'l10n_ro_export_saft_to_xml',
                'file_export_type': _('XML')
            })

    @api.model
    def l10n_ro_export_saft_to_xml(self, options):
        report = self.env['account.report'].browse(options['report_id'])
        values = self._l10n_ro_saft_prepare_report_values(report, options)
        file_data = self._saft_generate_file_data_with_error_check(
            report, options, values, 'l10n_ro_saft.saft_template'
        )
        return file_data

    @api.model
    def _l10n_ro_saft_check_report_values(self, values, options):
        values['errors'] = [
            *self._l10n_ro_saft_check_header_values(options, values),
            *self._l10n_ro_saft_check_partner_values(values),
            *self._l10n_ro_saft_check_tax_values(values),
            *self._l10n_ro_saft_check_product_values(values),
        ]

    @api.model
    def _l10n_ro_saft_prepare_report_values(self, report, options):
        values = self._saft_prepare_report_values(report, options)

        self._l10n_ro_saft_fill_header_values(options, values)
        self._l10n_ro_saft_fill_partner_values(values)
        self._l10n_ro_saft_fill_tax_values(values)
        self._l10n_ro_saft_fill_uom_values(values)
        self._l10n_ro_saft_fill_product_values(values)
        self._l10n_ro_saft_fill_account_code_by_id(values)
        self._l10n_ro_saft_fill_invoice_values(values)
        self._l10n_ro_saft_fill_payment_values(values)
        self._l10n_ro_saft_check_report_values(values, options)

        return values

    @api.model
    def _l10n_ro_saft_check_header_values(self, options, values):
        """ Check whether the company configuration is correct for filling in the Header. """
        def get_company_action(message):
            return {
                'message': message,
                'action_text': _('View Company'),
                'action_name': 'saft_action_open_company',
                'action_params': values['company'].id,
            }

        errors = []

        # The company must have a Tax Accounting Basis defined.
        if not values['company'].l10n_ro_saft_tax_accounting_basis:
            errors.append({
                'message': _('Please set the company Tax Accounting Basis.'),
                'action_text': _('View Settings'),
                'action_name': 'action_open_settings',
                'action_params': values['company'].id,
            })

        # The company must have a bank account defined.
        if not values['company'].bank_ids:
            errors.append({
                'message': _('Please define a `Bank Account` for your company.'),
                'action_text': _('Set Bank Account'),
                'action_name': 'action_open_partner_company',
                'action_params': values['company'].partner_id.id,
            })

        # The company must have a telephone number defined.
        if not values['company'].partner_id.phone and not values['company'].partner_id.mobile:
            errors.append(get_company_action(_('Please define a `Telephone Number` for your company.')))

        # The company must either have a VAT number defined (if it is registered for VAT in Romania),
        # or have its CUI number in the company_registry field (if not registered for VAT).
        partner = values['company'].partner_id
        if partner.vat:
            if not stdnum.ro.cf.is_valid(partner.vat):
                errors.append(get_company_action(_('The VAT number for your company is incorrect.')))
        elif partner.company_registry:
            if not stdnum.ro.cui.is_valid(partner.company_registry):
                errors.append(get_company_action(_('The CUI number for your company (under `Company Registry` in the Company settings) is incorrect.')))
        else:
            errors.append(get_company_action(_('In the Company settings, please set your company VAT number under `Tax ID` if registered for VAT, or your CUI number under `Company Registry`.')))

        return errors

    @api.model
    def _l10n_ro_saft_fill_header_values(self, options, values):
        """ Fill in header values """
        # Mandatory values for the D.406 declaration
        values.update({
            'xmlns': 'mfp:anaf:dgti:d406:declaratie:v1',
            'file_version': '2.4.7',
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
        # - C for returns on request
        # - NL for non-residents monthly
        # - NT for non-residents quarterly
        if values['company'].country_code == 'RO':
            declaration_type = {
                'month': 'L',
                'quarter': 'T',
                'year': 'A',
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
        faulty_partners = defaultdict(lambda: self.env['res.partner'])
        for partner_vals in values['partner_detail_map'].values():
            partner = partner_vals['partner']
            # Partner addresses must include the City and Country.
            if not partner.city:
                faulty_partners[_('These partner addresses are missing the city:')] |= partner
            if not partner.country_code:
                faulty_partners[_('These partner addresses are missing the country:')] |= partner
            # Partner country code should match the VAT prefix, if the VAT number is provided
            elif partner.vat and partner.vat[:2].isalpha() and partner.country_code.lower() != partner._split_vat(partner.vat)[0]:
                faulty_partners[_('These partners have a VAT prefix that differs from their country:')] |= partner
            # Romanian company partners should have their VAT number or CUI number set in the Tax ID or company_registry field.
            # Foreign company partners should have their VAT number set in the Tax ID field.
            if partner.is_company:
                if not partner.vat:
                    vat_country, vat_number = 'ro', ''
                elif not partner.vat[:2].isalpha():
                    vat_country, vat_number = 'ro', partner.vat
                else:
                    vat_country, vat_number = partner._split_vat(partner.vat)
                if partner.country_code == 'RO' or not partner.country_code:
                    cui = partner.company_registry or vat_number
                    if not stdnum.ro.cui.is_valid(cui):
                        faulty_partners[_('Some partners have missing or invalid CUI numbers in `Company Registry`. '
                                          'Example of a valid CUI: 18547290')] |= partner
                elif not partner.vat or not partner.simple_vat_check(vat_country, vat_number):
                    faulty_partners[_('Some partners have missing or invalid VAT numbers. '
                                      'Example of a valid VAT: RO18547290')] |= partner
                elif partner.perform_vies_validation and not partner.vies_valid:
                    faulty_partners[_('The VAT numbers for the following partners failed the VIES check:')] |= partner

        return [
            {'message': message, 'action_text': _('View Partners'), 'action_name': 'action_open_partners', 'action_params': partners.ids}
            for message, partners in faulty_partners.items()
        ]

    @api.model
    def _l10n_ro_saft_fill_partner_values(self, values):
        """ Fill in partner-related values in the values dict, performing checks as we go. """

        def get_registration_number(partner):
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
                    return '04' + partner.country_code + str(partner.id)
                elif partner.country_id in partner.env.ref('base.europe').country_ids:
                    return '05' + partner.country_code + str(partner.id)
                else:
                    return '06' + partner.country_code + str(partner.id)
                # Code 08 (unidentified customer in PoS transactions) not implemented because the PoS does
                # not generate anonymous invoices.

        for partner_vals in values['partner_detail_map'].values():
            partner_vals['registration_number'] = get_registration_number(partner_vals['partner'])
            partner_vals['l10n_ro_saft_contacts'] = partner_vals['contacts'].filtered(
                # Only provide partners which have a first name, last name and phone number.
                lambda contact: ' ' in contact.name[1:-1] and (contact.phone or contact.mobile)
            )

    @api.model
    def _l10n_ro_saft_check_tax_values(self, values):
        """ Check whether all taxes have a Romanian SAFT tax type and tax code on them. """
        encountered_tax_ids = [tax_vals['id'] for tax_vals in values['tax_vals_list']]
        faulty_taxes = self.env['account.tax'].search([
            ('id', 'in', encountered_tax_ids),
            '|', ('l10n_ro_saft_tax_type_id', '=', False), ('l10n_ro_saft_tax_code', '=', False)
        ])
        errors = []
        if faulty_taxes:
            errors.append({
                'message': _('Some taxes are missing the "Romanian SAF-T Tax Type" '
                             'and/or "Romanian SAF-T Tax Code" field(s).'),
                'action_text': _('View Taxes'),
                'action_name': 'action_open_taxes',
                'action_params': faulty_taxes.ids,
            })
        return errors

    @api.model
    def _l10n_ro_saft_fill_tax_values(self, values):
        """ Fill in the Romanian tax type, tax type description (in Romanian, if available), and tax code. """
        encountered_tax_ids = [tax_vals['id'] for tax_vals in values['tax_vals_list']]
        encountered_taxes = self.env['account.tax'].with_context({'lang': 'ro_RO'}).browse(encountered_tax_ids)
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

    @api.model
    def _l10n_ro_saft_fill_uom_values(self, values):
        """ Fill UoMs and unece_code_by_uom """
        encountered_product_uom_ids = sorted({
            line_vals['product_uom_id']
            for move_vals in values['move_vals_list']
            for line_vals in move_vals['line_vals_list']
            if line_vals['product_uom_id']
        })
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
        def get_product_action(message, product_ids, critical=False):
            return {
                'message': message,
                'action_text': _('View Products'),
                'action_name': 'action_open_products',
                'action_params': product_ids,
                'critical': critical,
            }

        encountered_product_ids = sorted({
            line_vals['product_id']
            for move_vals in values['move_vals_list']
            for line_vals in move_vals['line_vals_list']
            if line_vals['product_id']
        })
        encountered_products = self.env['product.product'].browse(encountered_product_ids)
        product_refs = encountered_products.mapped('default_code')
        products_no_ref = encountered_products.filtered(lambda product: not product.default_code)
        products_dup_ref = (encountered_products - products_no_ref).filtered(lambda product: product_refs.count(product.default_code) >= 2)

        errors = []
        if products_no_ref:
            errors.append(get_product_action(
                _('Some products have no `Internal Reference`.'),
                products_no_ref.ids,
                critical=True
            ))
        if products_dup_ref:
            errors.append(get_product_action(
                _('Some products have duplicated `Internal Reference`, please make them unique.'),
                products_dup_ref.ids,
                critical=True
            ))
        if 'intrastat_code_id' not in encountered_products:  # intrastat module isn't installed, don't check for the instrastat code
            return errors

        products_without_intrastat_code = encountered_products.filtered(lambda p: p.type != 'service' and not p.intrastat_code_id)
        if products_without_intrastat_code:
            errors.append(get_product_action(
                _("The Intrastat code isn't set on some products."),
                products_without_intrastat_code.ids
            ))

        return errors

    @api.model
    def _l10n_ro_saft_fill_product_values(self, values):
        """ Fill product_vals_list """
        encountered_product_ids = sorted({
            line_vals['product_id']
            for move_vals in values['move_vals_list']
            for line_vals in move_vals['line_vals_list']
            if line_vals['product_id']
        })
        encountered_products = self.env['product.product'].browse(encountered_product_ids)
        product_vals_list = [
            {
                'id': product.id,
                'name': product.name,
                'default_code': product.default_code,
                'uom_id': product.uom_id.id,
                'product_category': product.product_tmpl_id.categ_id.name,
                # The account_intrastat module is not a dependency, so this code should work regardless of whether it is installed.
                'commodity_code': '00000000' if product.type == 'service' else
                                  (product.intrastat_code_id.code if 'intrastat_code_id' in product and product.intrastat_code_id else '0'),
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

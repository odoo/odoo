# -*- coding: utf-8 -*-
from odoo import api, Command, fields, models, _


class AccountBusinessLineMixin(models.AbstractModel):
    ''' Mixin te be used by any business model lines like invoices, SO, PO etc in order to have unified behavior
    thanks to helpers defined in this class, specially to manage taxes including:
    - computation of the correct price unit from product when taxes are mapped using a fiscal position.
    - computation of the same tax amount when dealing with round_globally.
    '''
    _name = 'account.business.line.mixin'
    _description = "Business Lines Helpers"

    # -------------------------------------------------------------------------
    # TO BE OVERRIDDEN METHODS
    # -------------------------------------------------------------------------

    def _get_product(self):
        # TO BE OVERRIDDEN
        return self.env['product.product']

    def _get_product_uom(self):
        # TO BE OVERRIDDEN
        return self.env['uom.uom']

    def _get_taxes(self):
        # TO BE OVERRIDDEN
        return self.env['account.tax']

    def _get_price_unit(self):
        # TO BE OVERRIDDEN
        return None

    def _get_quantity(self):
        # TO BE OVERRIDDEN
        return None

    def _get_discount(self):
        # TO BE OVERRIDDEN
        return None

    def _get_partner(self):
        # TO BE OVERRIDDEN
        return self.env['res.partner']

    def _get_company(self):
        # TO BE OVERRIDDEN
        return self.env['res.company']

    def _get_currency(self):
        # TO BE OVERRIDDEN
        return self.env['res.currency']

    def _get_account(self):
        # TO BE OVERRIDDEN
        return self.env['account.account']

    def _get_analytic_account(self):
        # TO BE OVERRIDDEN
        return self.env['account.analytic.account']

    def _get_analytic_tags(self):
        # TO BE OVERRIDDEN
        return self.env['account.analytic.tag']

    def _get_journal(self):
        # TO BE OVERRIDDEN
        return self.env['account.journal']

    def _get_date(self):
        # TO BE OVERRIDDEN
        return None

    def _get_fiscal_position(self):
        # TO BE OVERRIDDEN
        return self.env['account.fiscal.position']

    def _get_tax_repartition_line(self):
        # TO BE OVERRIDDEN
        return self.env['account.tax.repartition.line']

    def _get_tags(self):
        # TO BE OVERRIDDEN
        return self.env['account.account.tag']

    def _get_document_type(self):
        # TO BE OVERRIDDEN
        return None

    def _is_refund_document(self):
        # TO BE OVERRIDDEN
        return False

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_default_product_name(self):
        ''' Helper to get the default name of a business line based on the product.
        :return: A string.
        '''
        company = self._get_company()
        if company:
            self = self.with_company(company)

        product = self._get_product()
        partner = self._get_partner()

        if not product:
            return ''

        if partner.lang:
            product = product.with_context(lang=partner.lang)

        values = []
        if product.partner_ref:
            values.append(product.partner_ref)
        if self._get_document_type() == 'sale':
            if product.description_sale:
                values.append(product.description_sale)
        elif self._get_document_type() == 'purchase':
            if product.description_purchase:
                values.append(product.description_purchase)
        return '\n'.join(values)

    def _get_default_product_uom(self):
        ''' Helper to get the default unit of measure of a business line based on the product.
        :return: An uom.uom record or an empty recordset.
        '''
        company = self._get_company()
        if company:
            self = self.with_company(company)

        product = self._get_product()
        return product.uom_id

    def _get_default_product_account(self):
        ''' Helper to get the default accounting account of a business line based on the product.
        :return: An account.account record or an empty recordset.
        '''
        company = self._get_company()
        if company:
            self = self.with_company(company)

        product = self._get_product()
        journal = self._get_journal()
        fiscal_position = self._get_fiscal_position()

        if product:
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if self._get_document_type() == 'sale':
                account = accounts['income']
            elif self._get_document_type() == 'purchase':
                account = accounts['expense']
            else:
                account = self.env['account.account']
        else:
            account = self.env['account.account']

        if not account and journal:
            account = journal.default_account_id

        return account

    def _get_default_taxes(self):
        ''' Helper to get the default taxes of a business line.
        :return: An account.tax recordset.
        '''
        company = self._get_company()
        if company:
            self = self.with_company(company)

        product = self._get_product()
        company = self._get_company()
        fiscal_position = self._get_fiscal_position()
        partner = self._get_partner()
        account = self._get_account()

        if self._get_document_type() == 'sale':
            taxes = product.taxes_id
        elif self._get_document_type() == 'purchase':
            taxes = product.supplier_taxes_id
        else:
            taxes = self.env['account.tax']

        if company:
            taxes = taxes.filtered(lambda tax: tax.company_id == company)

        if not taxes:
            taxes = account.tax_ids

        if not taxes:
            if self._get_document_type() == 'sale':
                taxes = company.account_sale_tax_id
            elif self._get_document_type() == 'purchase':
                taxes = company.account_purchase_tax_id

        if taxes and fiscal_position:
            taxes = fiscal_position.map_tax(taxes, partner=partner)

        return taxes

    def _get_default_product_price_unit(self):
        ''' Helper to get the default price unit of a business line based on the product.
        :return: The price unit.
        '''
        company = self._get_company()
        if company:
            self = self.with_company(company)

        product = self._get_product()
        partner = self._get_partner()
        uom = self._get_product_uom()
        product_uom = self._get_default_product_uom()
        currency = self._get_currency()
        company = self._get_company()
        product_currency = product.company_id.currency_id or company.currency_id
        fiscal_position = self._get_fiscal_position()
        is_refund_document = self._is_refund_document()
        date = self._get_date()

        if not product:
            return 0.0

        if self._get_document_type() == 'sale':
            price_unit = product.lst_price
            product_taxes = product.taxes_id
        elif self._get_document_type() == 'purchase':
            price_unit = product.standard_price
            product_taxes = product.supplier_taxes_id
        else:
            return 0.0

        if company:
            product_taxes = product_taxes.filtered(lambda tax: tax.company_id == company)

        # Apply unit of measure.
        if uom and uom != product_uom:
            price_unit = product_uom._compute_price(price_unit, uom)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes, partner=partner)

            if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                flattened_taxes = product_taxes._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes):
                    taxes_res = flattened_taxes.compute_all(
                        price_unit,
                        quantity=1.0,
                        currency=product_currency,
                        product=product,
                        partner=partner,
                        is_refund=is_refund_document,
                    )
                    price_unit = product_currency.round(taxes_res['total_excluded'])

                flattened_taxes = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes):
                    taxes_res = flattened_taxes.compute_all(
                        price_unit,
                        quantity=1.0,
                        currency=product_currency,
                        product=product,
                        partner=partner,
                        is_refund=is_refund_document,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            price_unit += tax_res['amount']

        # Apply currency rate.
        if currency and currency != product_currency and date:
            price_unit = product_currency._convert(price_unit, currency, company, date)

        return price_unit

    def _get_price_unit_without_discount(self):
        ''' Helper to get the default price unit reduced by the discount amount of a business line based on the product.
        :return: The price unit minus the discount.
        '''
        company = self._get_company()
        if company:
            self = self.with_company(company)

        price_unit = self._get_price_unit()
        discount = self._get_discount()

        if price_unit is None:
            return None

        if discount is None:
            return price_unit
        else:
            return price_unit * (1 - (discount / 100.0))

    # -------------------------------------------------------------------------
    # TAXES
    # -------------------------------------------------------------------------

    def _get_tax_detail_from_base_line(self, tax_vals):
        ''' Take a tax results returned by the taxes computation method and return values in order to create
        the corresponding account.tax.detail.

        :param tax_vals:    A python dict returned by 'compute_all' under the 'taxes' key.
        :return:            A python dict.
        '''
        self.ensure_one()
        tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
        return {
            'account_id': (tax_repartition_line._get_business_account() or self._get_account()).id,
            'currency_id': self._get_currency().id,
            'tax_repartition_line_id': tax_vals['tax_repartition_line_id'],
            'tax_id': tax_vals['group'].id if tax_vals['group'] else tax_repartition_line.tax_id.id,
            'tax_ids': [Command.set(tax_vals['tax_ids'])],
            'tag_ids': [Command.set(tax_vals['tag_ids'])],
            'tax_base_amount': tax_vals['base'],
            'tax_amount': tax_vals['amount'],
        }

    @api.model
    def _get_tax_grouping_key_from_tax_detail(self, tax_detail):
        ''' Method used to aggregate the tax details together in order to get the tax lines.

        :param tax_detail:  A python dict containing the values of an account.tax.detail record.
        :return:            A python dict representing the grouping key used to aggregate or modify tax lines.
        '''
        source_line = tax_detail['source_line']
        tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_detail['tax_repartition_line_id'])
        tax = tax_repartition_line.tax_id
        return {
            'tax_repartition_line_id': tax_detail['tax_repartition_line_id'],
            'account_id': tax_detail['account_id'],
            'company_id': source_line._get_company().id,
            'partner_id': source_line._get_partner().id,
            'currency_id': source_line._get_currency().id,
            'analytic_tag_ids': [Command.set(source_line._get_analytic_tags().ids)] if tax.analytic else [],
            'analytic_account_id': source_line._get_analytic_account().id if tax.analytic else False,
            'tax_ids': [Command.set(tax_detail['tax_ids'])],
            'tag_ids': [Command.set(tax_detail['tag_ids'])],
        }

    def _get_tax_grouping_key_from_tax_line(self):
        ''' Method used to find an existing tax line that is currently matching the grouping key created for a tax
        detail to avoid creating new tax lines every time.

        :return: A python dict representing the grouping key used to update an existing tax line.
        '''
        self.ensure_one()
        repartition_line = self._get_tax_repartition_line()
        tax = repartition_line.tax_id
        return {
            'tax_repartition_line_id': self._get_tax_repartition_line().id,
            'account_id': self._get_account().id,
            'company_id': self._get_company().id,
            'partner_id': self._get_partner().id,
            'currency_id': self._get_currency().id,
            'analytic_tag_ids': [Command.set(self._get_analytic_tags().ids)] if tax.analytic else [],
            'analytic_account_id': self._get_analytic_account().id if tax.analytic else False,
            'tax_ids': [Command.set(self._get_taxes().ids)],
            'tag_ids': [Command.set(self._get_tags().ids)],
        }

    def _prepare_tax_details(self):
        ''' Compute the tax details for the current base lines.

        :return: A list of python dictionaries containing:
            * <The result of the compute_all method as kwargs>
            * source_line:  The business line record.
            * tax_details:  A list of python dictionary containing:
                * <A tax detail returned by the compute_all method as kwargs>
                * <The values returned by _get_tax_detail_from_base_line')
                * tax_base_amount:  The base tax amount.
                * tax_amount:       The tax amount.
        '''
        base_lines = self.filtered(lambda line: not line._get_tax_repartition_line())
        res = []
        for line in base_lines:
            taxes_res = line._get_taxes()._origin.compute_all(
                line._get_price_unit_without_discount(),
                currency=line._get_currency(),
                quantity=line._get_quantity(),
                product=line._get_product(),
                partner=line._get_partner(),
                is_refund=line._is_refund_document(),
                handle_price_include=line._get_document_type() in ('sale', 'purchase'),
            )

            line_details = {
                **taxes_res,
                'source_line': line,
                'tax_details': [],
            }
            res.append(line_details)
            for tax_vals in taxes_res['taxes']:
                line_details['tax_details'].append(line._get_tax_detail_from_base_line(tax_vals))
        return res

    def _prepare_diff_tax_lines(self, tax_details_list):
        ''' Aggregate the values of tax details passed as parameter to create the accounting tax lines if necessary.

        :param tax_details_list:    A list of dictionaries, each one created from an account.tax.detail or by the
                                    '_get_tax_detail_from_base_line' method.
        :return:                    A list of python dictionaries containing:
                                    * source_line:  The business line record.
                                    * command:      The orm command to be used in order to apply this difference to the
                                                    current business lines.
        '''
        def _serialize_python_dictionary(dict):
            return '-'.join(str(v) for v in dict.values())

        tax_details = {}
        tax_line_details = []

        # =========================================================================================
        # TAX DETAILS
        # =========================================================================================

        for tax_detail in tax_details_list:
            map_key_vals = self._get_tax_grouping_key_from_tax_detail(tax_detail)
            map_key = _serialize_python_dictionary(map_key_vals)

            tax_details.setdefault(map_key, {
                **tax_detail,
                **map_key_vals,
                'tax_base_amount': 0.0,
                'tax_amount': 0.0,
                'source_dicts': [],
            })
            tax_details[map_key]['tax_base_amount'] += tax_detail['tax_base_amount']
            tax_details[map_key]['tax_amount'] += tax_detail['tax_amount']
            tax_details[map_key]['source_dicts'].append(tax_detail)

        # =========================================================================================
        # TAX LINES
        # =========================================================================================

        # Track the existing tax lines using the grouping key.
        tax_lines = self.filtered(lambda line: line._get_tax_repartition_line())
        existing_tax_line_map = {}
        for line in tax_lines:
            map_key = _serialize_python_dictionary(line._get_tax_grouping_key_from_tax_line())

            # After a modification (e.g. changing the analytic account of the tax line), two tax lines are sharing the
            # same key. Keep only one.
            if map_key in existing_tax_line_map:
                tax_line_details.append({
                    'source_line': line,
                    'command': Command.delete(line.id),
                })
                continue

            existing_tax_line_map[map_key] = line

        # Update/create the tax lines.
        for map_key, tax_details_vals in tax_details.items():
            if map_key in existing_tax_line_map:
                # Update an existing tax line.
                existing_tax_line = existing_tax_line_map.pop(map_key)
                tax_line_details.append({
                    'source_line': existing_tax_line,
                    'source_dicts': tax_details_vals['source_dicts'],
                    'command': Command.update(existing_tax_line.id, {
                        'tax_base_amount': tax_details_vals['tax_base_amount'],
                        'tax_amount': tax_details_vals['tax_amount'],
                    }),
                })
            else:
                # Create a new tax line.
                tax_rep = self.env['account.tax.repartition.line'].browse(tax_details_vals['tax_repartition_line_id'])
                tax_line_details.append({
                    'source_dicts': tax_details_vals['source_dicts'],
                    'command': Command.create({
                        'name': tax_rep.tax_id.name,
                        'account_id': tax_details_vals['account_id'],
                        'currency_id': tax_details_vals['currency_id'],
                        'tax_amount': tax_details_vals['tax_amount'],
                        'tax_base_amount': tax_details_vals['tax_base_amount'],
                        'tax_ids': tax_details_vals['tax_ids'],
                        'tag_ids': tax_details_vals['tag_ids'],
                        'tax_repartition_line_id': tax_details_vals['tax_repartition_line_id'],
                        'company_id': tax_details_vals['company_id'],
                        'partner_id': tax_details_vals['partner_id'],
                        'analytic_tag_ids': tax_details_vals['analytic_tag_ids'],
                        'analytic_account_id': tax_details_vals['analytic_account_id'],
                        'tax_exigible': tax_rep.tax_id.tax_exigibility != 'on_payment',
                    }),
                })

        for existing_tax_line in existing_tax_line_map.values():
            tax_line_details.append({
                'source_line': existing_tax_line,
                'command': Command.delete(existing_tax_line.id),
            })

        return tax_line_details

    def _prepare_diff_tax_lines_from_tax_details(self):
        ''' Same as '_prepare_diff_tax_lines' but using the account.tax.detail recordset passed as parameter.

        :param tax_details: A recordset of account.tax.detail.
        :return:            See '_prepare_diff_tax_lines'.
        '''
        tax_details_list = []
        for tax_detail in self.tax_detail_ids:
            tax_details_list.append({
                'source_line': tax_detail.line_id,
                'source_record': tax_detail,
                'account_id': tax_detail.account_id.id,
                'currency_id': tax_detail.line_id.currency_id.id,
                'tax_amount': tax_detail.tax_amount_currency,
                'tax_base_amount': tax_detail.tax_base_amount_currency,
                'tax_ids': tax_detail.tax_ids.ids,
                'tag_ids': tax_detail.tag_ids.ids,
                'tax_repartition_line_id': tax_detail.tax_repartition_line_id.id,
            })
        return self._prepare_diff_tax_lines(tax_details_list)

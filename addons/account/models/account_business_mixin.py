# -*- coding: utf-8 -*-
from collections import defaultdict

from odoo import _, api, fields, models, Command
from odoo.tools.misc import formatLang


class AccountBusinessMixin(models.AbstractModel):
    _name = 'account.business.mixin'
    _description = """
    Generic class containing a lot of helpers used to ease some business computations and unify some behavior
    between the different business models.

    Each business model must override the '_get_business_values' method.
    """

    # -------------------------------------------------------------------------
    # TO BE OVERRIDDEN
    # -------------------------------------------------------------------------

    def _get_business_values(self):
        """ Convert the current record to a python dictionary unifying the business fields. It could contains:

        'record':               Set by default to retrieve the current record when overriding this method in other modules.

        'journal':              Optional: An account.journal record.
        'date':                 Required: The business date of the document.
        'fiscal_position':      Optional: An account.fiscal.position record.
        'partner':              Optional: The res.partner linked to the document.
        'delivery_partner':     Optional: The res.partner acting as a delivery address.
        'currency':             Required: The res.currency of the business document.
        'document_type':        Required: One of the following values: ('sale', 'purchase', None).
        'company':              Required: The res.company of the business document.
        'is_refund':            Optional: Flag indicating the business document is a refund.
        'handle_price_include': Optional: Flag indicating the price included taxes are managed or not.
        'include_caba_tags':    Optional: Flag indicating the cash basis tags should be included or not.

        'product':              Optional: A product.product record.
        'product_uom':          Optional: An uom.uom record.
        'taxes':                Optional: The account.tax records applied to the business document.
        'price_unit':           Required: The unit price.
        'quantity':             Required: The quantity.
        'discount':             Optional: The discount.
        'account':              Optional: An account.account record.
        'analytic_account':     Optional: An account.analytic.account record.
        'analytic_tags':        Optional: account.analytic.tag records.
        'tax_tags':             Optional: The account.account.tag records got when computing taxes.

        Optional fields used only for account.move tax lines:
        'price_subtotal':       Optional: The price subtotal of the current record.
        'tax_id':               Optional: The account.tax applied to this tax line.
        'tax_repartition_line': Optional: The account.tax.repartition.line applied to this tax line.

        :return: A python dict.
        """
        self.ensure_one()

        return {'record': self}

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _get_default_product_name_lines(self):
        """ Get a list of text to be aggregated together to compute the default label based on a product.

        :return: A list of string.
        """
        business_vals = self._get_business_values()
        product = business_vals.get('product')
        partner = business_vals.get('partner')

        if not product:
            return []

        if partner and partner.lang:
            product = product.with_context(lang=partner.lang)

        text_lines = []
        if product.partner_ref:
            text_lines.append(product.partner_ref)
        if business_vals['document_type'] == 'sale':
            if product.description_sale:
                text_lines.append(product.description_sale)
        elif business_vals['document_type'] == 'purchase':
            if product.description_purchase:
                text_lines.append(product.description_purchase)
        return text_lines

    def _get_default_product_name(self):
        """ Get the default label based on a product.

        :return: A string.
        """
        return '\n'.join(self._get_default_product_name_lines())

    def _get_default_product_uom(self):
        """ Get the default product uom.

        :return: A product.uom recordset of length [0, 1].
        """
        business_vals = self._get_business_values()
        product = business_vals.get('product')
        return product.uom_id if product else self.env['product.uom']

    def _get_default_product_account(self):
        """ Get the default account.

        :return: An account.account recordset of length [0, 1].
        """
        business_vals = self._get_business_values()
        company = business_vals.get('company')
        journal = business_vals.get('journal')
        fiscal_position = business_vals.get('fiscal_position')
        product = business_vals.get('product')
        document_type = business_vals.get('document_type')

        if company:
            product = product.with_company(company)

        if product:
            accounts = product.product_tmpl_id.get_product_accounts(fiscal_pos=fiscal_position)
            if document_type == 'sale':
                account = accounts['income']
            elif document_type == 'purchase':
                account = accounts['expense']
            else:
                account = self.env['account.account']
        else:
            account = self.env['account.account']

        if not account and journal:
            account = journal.default_account_id

        return account

    def _get_default_taxes(self):
        """ Get the default taxes.

        :return: An account.tax recordset.
        """
        business_vals = self._get_business_values()
        company = business_vals.get('company')
        fiscal_position = business_vals.get('fiscal_position')
        product = business_vals.get('product')
        account = business_vals.get('account')
        document_type = business_vals.get('document_type')

        if product and document_type == 'sale':
            taxes = product.taxes_id
        elif product and document_type == 'purchase':
            taxes = product.supplier_taxes_id
        else:
            taxes = self.env['account.tax']

        if company:
            taxes = taxes.filtered(lambda tax: tax.company_id == company)

        if not taxes and account:
            taxes = account.tax_ids

        if not taxes and company:
            if document_type == 'sale':
                taxes = company.account_sale_tax_id
            elif document_type == 'purchase':
                taxes = company.account_purchase_tax_id

        if taxes and fiscal_position:
            taxes = fiscal_position.map_tax(taxes)

        return taxes

    def _get_default_product_price_unit(self):
        """ Get the default price_unit computed from the product.

        :return: A tuple <price_unit, currency, uom> where 'price_unit' is the unit price expressed in the 'currency'
        using the 'uom' unit of measure.
        """
        business_vals = self._get_business_values()
        company = business_vals.get('company')
        product = business_vals.get('product')
        document_type = business_vals.get('document_type')

        if not product:
            return 0.0, None, None

        if document_type == 'sale':
            price_unit = product.lst_price
        elif document_type == 'purchase':
            price_unit = product.standard_price
        else:
            return 0.0, None, None

        product_uom = self._get_default_product_uom()
        product_currency = product.company_id.currency_id or (company and company.currency_id)
        return price_unit, product_currency, product_uom

    def _get_default_price_unit(self):
        """ Get the default price_unit to be set on the business object.

        :return: A float.
        """
        business_vals = self._get_business_values()
        company = business_vals.get('company')
        fiscal_position = business_vals.get('fiscal_position')
        date = business_vals.get('date') or fields.Date.context_today(self)
        is_refund = business_vals.get('is_refund')
        product = business_vals.get('product')
        product_uom = business_vals.get('product_uom')
        partner = business_vals.get('partner')
        currency = business_vals.get('currency')
        quantity = business_vals.get('quantity', 1.0)
        document_type = business_vals.get('document_type')

        if not product:
            return 0.0

        price_unit, default_product_currency, default_product_uom = self._get_default_product_price_unit()
        if document_type == 'sale':
            product_taxes = product.taxes_id
        elif document_type == 'purchase':
            product_taxes = product.supplier_taxes_id
        else:
            return 0.0

        if product_taxes and company:
            product_taxes = product_taxes.filtered(lambda tax: tax.company_id == company)

        # Apply unit of measure.
        if product_uom and product_uom != default_product_uom:
            price_unit = default_product_uom._compute_price(price_unit, product_uom)

        # Apply fiscal position.
        if product_taxes and fiscal_position:
            product_taxes_after_fp = fiscal_position.map_tax(product_taxes)

            if set(product_taxes.ids) != set(product_taxes_after_fp.ids):
                flattened_taxes = product_taxes._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes):
                    taxes_res = flattened_taxes.with_context(round=False).compute_all(
                        price_unit,
                        quantity=quantity,
                        currency=default_product_currency,
                        product=product,
                        partner=partner,
                        is_refund=is_refund,
                    )
                    price_unit = (taxes_res['total_excluded'] / quantity) if quantity else 0.0

                flattened_taxes = product_taxes_after_fp._origin.flatten_taxes_hierarchy()
                if any(tax.price_include for tax in flattened_taxes):
                    taxes_res = flattened_taxes.compute_all(
                        price_unit,
                        quantity=quantity,
                        currency=default_product_currency,
                        product=product,
                        partner=partner,
                        is_refund=is_refund,
                        handle_price_include=False,
                    )
                    for tax_res in taxes_res['taxes']:
                        tax = self.env['account.tax'].browse(tax_res['id'])
                        if tax.price_include:
                            price_unit += (tax_res['amount'] / quantity) if quantity else 0.0

        # Apply currency rate.
        if currency and default_product_currency and currency != default_product_currency:
            price_unit = default_product_currency._convert(price_unit, currency, company, date)

        return price_unit

    def _get_price_unit_without_discount(self):
        """ Get the price unit after subtracting the discount.

        :return: A float.
        """
        business_vals = self._get_business_values()
        price_unit = business_vals.get('price_unit')
        discount = business_vals.get('discount')

        if price_unit is None:
            return 0.0

        if discount is None:
            return price_unit
        else:
            return price_unit * (1 - (discount / 100.0))

    def _get_default_delivery_partner(self):
        """ Get the default delivery address.

        :return: An res.partner recordset of length [0, 1].
        """
        business_vals = self._get_business_values()
        partner = business_vals.get('partner')
        if partner:
            return self.env['res.partner'].browse(partner.address_get(['delivery'])['delivery'])
        else:
            return self.env['res.partner']

    def _get_default_invoicing_partner(self):
        """ Get the default invoicing partner.

        :return: An res.partner recordset of length [0, 1].
        """
        business_vals = self._get_business_values()
        partner = business_vals.get('partner')
        if partner:
            return self.env['res.partner'].browse(partner.address_get(['invoice'])['invoice'])
        else:
            return self.env['res.partner']

    def _get_default_partner_payment_terms(self):
        """ Get the default partner's payment terms.

        :return: An account.payment.term recordset of length [0, 1].
        """
        business_vals = self._get_business_values()
        company = business_vals.get('company')
        partner = business_vals.get('partner')
        document_type = business_vals.get('document_type')

        if not partner:
            return self.env['account.payment.term']

        if document_type == 'sale':
            return partner.with_company(company).property_payment_term_id
        elif document_type == 'purchase':
            return partner.with_company(company).property_supplier_payment_term_id
        else:
            return self.env['account.payment.term']

    def _get_default_partner_fiscal_position(self):
        """ Get the default partner's fiscal position.

        :return: An account.fiscal.position recordset of length [0, 1].
        """
        business_vals = self._get_business_values()
        company = business_vals.get('company')
        partner = business_vals.get('partner')
        delivery_partner = business_vals.get('delivery_partner')

        if not delivery_partner:
            delivery_partner = self._get_default_delivery_partner()

        if partner:
            return self.env['account.fiscal.position'].with_company(company).get_fiscal_position(
                partner.id,
                delivery_id=delivery_partner.id if delivery_partner else None,
            )
        else:
            return self.env['account.fiscal.position']

    # -------------------------------------------------------------------------
    # TAXES
    # -------------------------------------------------------------------------

    @api.model
    def _get_tax_grouping_key_from_base_line(self, business_vals, tax_vals):
        ''' Take a tax results returned by the taxes computation method and return values in order to create
        the corresponding account.tax.detail.
        :param tax_vals:    A python dict returned by 'compute_all' under the 'taxes' key.
        :return:            A python dict.
        '''
        account = business_vals.get('account')
        partner = business_vals.get('partner')
        currency = business_vals.get('currency')
        tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_vals['tax_repartition_line_id'])
        tax_account = tax_repartition_line._get_business_tax_account() or account
        analytic_tags = business_vals.get('analytic_tags')
        analytic_account = business_vals.get('analytic_account')
        return {
            'account_id': tax_account and tax_account.id,
            'currency_id': currency and currency.id,
            'partner_id': partner and partner.id,
            'tax_repartition_line_id': tax_repartition_line.id,
            'tax_ids': [Command.set(tax_vals['tax_ids'])],
            'tax_tag_ids': [Command.set(tax_vals['tag_ids'])],
            'tax_id': (tax_vals['group'] or tax_repartition_line.tax_id).id,
            'analytic_tag_ids': tax_vals['analytic'] and analytic_tags and [Command.set(analytic_tags.ids)] or [],
            'analytic_account_id': tax_vals['analytic'] and analytic_account and analytic_account.id,
        }

    @api.model
    def _get_tax_grouping_key_from_tax_line(self, business_vals):
        ''' Method used to find an existing tax line that is currently matching the grouping key created for a tax
        detail to avoid creating new tax lines every time.
        :return: A python dict representing the grouping key used to update an existing tax line.
        '''
        account = business_vals.get('account')
        partner = business_vals.get('partner')
        currency = business_vals.get('currency')
        repartition_line = business_vals.get('tax_repartition_line')
        taxes = business_vals.get('taxes')
        tax_tags = business_vals.get('tax_tags')
        tax = business_vals.get('tax_id')
        tax_rep_tax = repartition_line.tax_id
        analytic_tags = business_vals.get('analytic_tags')
        analytic_account = business_vals.get('analytic_account')
        return {
            'account_id': account and account.id,
            'currency_id': currency and currency.id,
            'partner_id': partner and partner.id,
            'tax_repartition_line_id': repartition_line and repartition_line.id,
            'tax_ids': taxes and [Command.set(taxes.ids)] or [],
            'tax_tag_ids': tax_tags and [Command.set(tax_tags.ids)] or [],
            'tax_id': tax and tax.id,
            'analytic_tag_ids': tax_rep_tax.analytic and analytic_tags and [Command.set(analytic_tags.ids)] or [],
            'analytic_account_id': tax_rep_tax.analytic and analytic_account and analytic_account.id,
        }

    def _compute_taxes(self):
        def _serialize_python_dictionary(vals):
            return '-'.join(str(vals[k] or False) for k in sorted(vals.keys()))

        res = {
            'tax_lines_to_add': [],
            'tax_lines_to_delete': [],
            'tax_lines_to_update': [],
            'base_lines_to_update': [],
            'totals': defaultdict(lambda: {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
            }),
        }

        base_line_vals_list = []
        tax_line_vals_list = []
        for x in self:
            business_vals = x._get_business_values()
            if business_vals.get('tax_repartition_line'):
                tax_line_vals_list.append(business_vals)
            else:
                base_line_vals_list.append(business_vals)

        # =========================================================================================
        # BASE LINES
        # =========================================================================================

        base_line_map = {}
        for base_line_vals in base_line_vals_list:
            taxes = base_line_vals['taxes']
            price_unit_wo_discount = base_line_vals['record']._get_price_unit_without_discount()
            quantity = base_line_vals.get('quantity', 1.0)
            currency = base_line_vals['currency']

            if taxes:
                taxes_res = taxes._origin.compute_all(
                    price_unit_wo_discount,
                    currency=currency,
                    quantity=quantity,
                    product=base_line_vals.get('product'),
                    partner=base_line_vals.get('partner'),
                    is_refund=base_line_vals.get('is_refund', False),
                    handle_price_include=business_vals.get('handle_price_include', True),
                    include_caba_tags=business_vals.get('include_caba_tags', False),
                )

                to_update_vals = {
                    'tax_tag_ids': [Command.set(taxes_res['base_tags'])],
                    'price_subtotal': taxes_res['total_excluded'],
                    'price_total': taxes_res['total_included'],
                }

                for tax_res in taxes_res['taxes']:
                    grouping_dict = self._get_tax_grouping_key_from_base_line(base_line_vals, tax_res)
                    tax_res['grouping_dict'] = grouping_dict

                    grouping_key_str = _serialize_python_dictionary(grouping_dict)

                    base_line_map.setdefault(grouping_key_str, {
                        **tax_res['grouping_dict'],
                        'tax_base_amount': 0.0,
                        'tax_amount': 0.0,
                    })
                    base_line_map[grouping_key_str]['tax_base_amount'] += tax_res['base']
                    base_line_map[grouping_key_str]['tax_amount'] += tax_res['amount']
            else:
                price_subtotal = currency.round(price_unit_wo_discount * quantity)
                to_update_vals = {
                    'tax_tag_ids': [],
                    'price_subtotal': price_subtotal,
                    'price_total': price_subtotal,
                }

            res['base_lines_to_update'].append((base_line_vals, to_update_vals))
            if currency:
                res['totals'][currency]['amount_untaxed'] += to_update_vals['price_subtotal']

        # =========================================================================================
        # TAX LINES
        # =========================================================================================

        # Track the existing tax lines using the grouping key.
        existing_tax_line_map = {}
        for tax_line_vals in tax_line_vals_list:
            grouping_key_str = _serialize_python_dictionary(self._get_tax_grouping_key_from_tax_line(tax_line_vals))

            # After a modification (e.g. changing the analytic account of the tax line), two tax lines are sharing the
            # same key. Keep only one.
            if grouping_key_str in existing_tax_line_map:
                res['tax_lines_to_delete'].append(tax_line_vals)
            else:
                existing_tax_line_map[grouping_key_str] = tax_line_vals

        # Update/create the tax lines.
        for grouping_key_str, tax_values in base_line_map.items():
            if tax_values['currency_id']:
                currency = self.env['res.currency'].browse(tax_values['currency_id'])
                res['totals'][currency]['amount_tax'] += currency.round(tax_values['tax_amount'])

            if grouping_key_str in existing_tax_line_map:
                # Update an existing tax line.
                tax_line_vals = existing_tax_line_map.pop(grouping_key_str)
                res['tax_lines_to_update'].append((tax_line_vals, tax_values))
            else:
                # Create a new tax line.
                res['tax_lines_to_add'].append(tax_values)

        for tax_line_vals in existing_tax_line_map.values():
            res['tax_lines_to_delete'].append(tax_line_vals)

        return res

    @api.model
    def _aggregate_taxes_by_tax_group(self, vals_list):
        tax_group_mapping = defaultdict(lambda: {
            'base_lines': set(),
            'base_amount': 0.0,
            'tax_amount': 0.0,
        })

        for vals in vals_list:
            record = vals.get('record')
            amount = vals['amount']
            taxes = vals.get('taxes')
            originator_tax = vals.get('tax')

            # Compute tax amounts.

            if originator_tax:
                tax_group_vals = tax_group_mapping[originator_tax.tax_group_id]
                tax_group_vals['tax_amount'] += amount

            # Compute base amounts.

            if not taxes:
                continue

            for tax in taxes.flatten_taxes_hierarchy():

                if originator_tax and originator_tax.tax_group_id == tax.tax_group_id:
                    continue

                tax_group_vals = tax_group_mapping[tax.tax_group_id]
                if not record or (record and record not in tax_group_vals['base_lines']):
                    tax_group_vals['base_amount'] += amount
                    tax_group_vals['base_lines'].add(record)

        tax_groups = sorted(tax_group_mapping.keys(), key=lambda x: x.sequence)
        tax_group_vals_list = []
        for tax_group in tax_groups:
            tax_group_vals = tax_group_mapping[tax_group]

            tax_group_vals_list.append({
                'tax_group': tax_group,
                'tax_amount': tax_group_vals['tax_amount'],
                'base_amount': tax_group_vals['base_amount'],
            })
        return tax_group_vals_list

    def _prepare_tax_totals_json(self, recompute_taxes=True):
        """ Compute the tax totals details for the business documents.
        :param recompute_taxes: Indicate if the current

        :return: A dictionary in the following form:
            {
                'amount_total':                 The total amount to be displayed on the document, including every total
                                                types.
                'amount_untaxed':               The untaxed amount to be displayed on the document.
                'formatted_amount_total':       Same as amount_total, but as a string formatted accordingly with
                                                partner's locale.
                'formatted_amount_untaxed':     Same as amount_untaxed, but as a string formatted accordingly with
                                                partner's locale.
                'allow_tax_edition':            True if the user should have the ability to manually edit the tax amounts
                                                by group to fix rounding errors.
                'groups_by_subtotals':          A dictionary formed liked {'subtotal': groups_data}
                                                Where total_type is a subtotal name defined on a tax group, or the
                                                default one: 'Untaxed Amount'.
                                                And groups_data is a list of dict in the following form:
                    {
                        'tax_group_name':                   The name of the tax groups this total is made for.
                        'tax_group_amount':                 The total tax amount in this tax group.
                        'tax_group_base_amount':            The base amount for this tax group.
                        'formatted_tax_group_amount':       Same as tax_group_amount, but as a string formatted accordingly
                                                            with partner's locale.
                        'formatted_tax_group_base_amount':  Same as tax_group_base_amount, but as a string formatted
                                                            accordingly with partner's locale.
                        'tax_group_id':                     The id of the tax group corresponding to this dict.
                    }
                'subtotals':                    A list of dictionaries in the following form, one for each subtotal in
                                                'groups_by_subtotals' keys.
                    {
                        'name':                             The name of the subtotal
                        'amount':                           The total amount for this subtotal, summing all the tax groups
                                                            belonging to preceding subtotals and the base amount
                        'formatted_amount':                 Same as amount, but as a string formatted accordingly with
                                                            partner's locale.
                    }
            }
        """
        vals_list = []
        business_line_vals_list = [x._get_business_values() for x in self]

        if business_line_vals_list and business_line_vals_list[0].get('partner'):
            lang_env = self.with_context(lang=business_line_vals_list[0]['partner'].lang).env
        else:
            lang_env = self.env

        if business_line_vals_list and business_line_vals_list[0].get('currency'):
            currency = business_line_vals_list[0]['currency']
        else:
            currency = self.env.company.currency_id

        amount_untaxed = 0.0
        amount_tax = 0.0

        # ==== Recompute taxes on-the-fly for business models that are not creating any tax lines ====

        if recompute_taxes:
            tax_results = self._compute_taxes()

            for base_line_vals, to_update in tax_results['base_lines_to_update']:
                base_line_vals['price_subtotal'] = to_update['price_subtotal']

            for tax_line_vals in tax_results['tax_lines_to_add']:
                tax_ids = tax_line_vals['tax_ids'][0][2] if tax_line_vals['tax_ids'] else []
                tax_repartition_line = self.env['account.tax.repartition.line'].browse(tax_line_vals['tax_repartition_line_id'])

                vals_list.append({
                    'amount': tax_line_vals['tax_amount'],
                    'tax': tax_repartition_line.tax_id,
                    'taxes': self.env['account.tax'].browse(tax_ids),
                })

        # ==== Aggregate the tax values by tax group ====

        for business_line_vals in business_line_vals_list:
            tax_repartition_line = business_line_vals.get('tax_repartition_line')
            taxes = business_line_vals.get('taxes')

            if tax_repartition_line and recompute_taxes:
                continue
            if not tax_repartition_line and not taxes:
                continue

            vals_list.append({
                'record': business_line_vals['record'],
                'amount': business_line_vals['price_subtotal'],
                'taxes': taxes,
                'tax': tax_repartition_line.tax_id if tax_repartition_line else None,
            })

            if not tax_repartition_line:
                amount_untaxed += business_line_vals['price_subtotal']

        tax_group_vals_list = self._aggregate_taxes_by_tax_group(vals_list)

        # ==== Partition the tax group values by subtotals ====

        subtotal_order = {}
        groups_by_subtotal = {}
        for tax_group_vals in tax_group_vals_list:
            tax_group = tax_group_vals['tax_group']

            if tax_group.preceding_subtotal:
                subtotal_title = tax_group.preceding_subtotal
                sequence = tax_group.sequence + 1 # Avoid sequence = 0 here.
            else:
                subtotal_title = _("Untaxed Amount")
                sequence = 0

            if subtotal_title not in subtotal_order:
                subtotal_order[subtotal_title] = sequence
                groups_by_subtotal[subtotal_title] = []

            groups_by_subtotal[subtotal_title].append({
                'tax_group_id': tax_group.id,
                'tax_group_name': tax_group.name,
                'tax_group_amount': tax_group_vals['tax_amount'],
                'tax_group_base_amount': tax_group_vals['base_amount'],
                'formatted_tax_group_amount': formatLang(lang_env, tax_group_vals['tax_amount'], currency_obj=currency),
                'formatted_tax_group_base_amount': formatLang(lang_env, tax_group_vals['base_amount'], currency_obj=currency),
            })

        # ==== Build the final result ====

        subtotals = []
        for subtotal_title in sorted(subtotal_order.keys(), key=lambda k: subtotal_order[k]):
            amount_total = amount_untaxed + amount_tax
            subtotals.append({
                'name': subtotal_title,
                'amount': amount_total,
                'formatted_amount': formatLang(lang_env, amount_total, currency_obj=currency),
            })
            amount_tax += sum(x['tax_group_amount'] for x in groups_by_subtotal[subtotal_title])

        amount_total = amount_untaxed + amount_tax

        return {
            'amount_untaxed': amount_untaxed,
            'amount_total': amount_total,
            'formatted_amount_total': formatLang(lang_env, amount_total, currency_obj=currency),
            'formatted_amount_untaxed': formatLang(lang_env, amount_untaxed, currency_obj=currency),
            'groups_by_subtotal': groups_by_subtotal,
            'subtotals': subtotals,
            'allow_tax_edition': False,
        }

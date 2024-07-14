# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from datetime import datetime
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from . import product

_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def _process_order(self, order):
        for transaction in order['TransactionArray']['Transaction']:
            so = self.env['sale.order'].search(
                [('client_order_ref', '=', transaction['OrderLineItemID'])], limit=1)
            try:
                if not so:
                    so = self._process_order_new(order, transaction)
                    so._process_order_update(order)
            except Exception as e:
                message = _("Ebay could not synchronize order:\n%s", e)
                path = str(order)
                product._log_logging(self.env, message, "_process_order", path)
                _logger.exception(message)

    @api.model
    def _process_order_new(self, order, transaction):
        (partner, shipping_partner) = self._process_order_new_find_partners(order)
        fp = self.env['account.fiscal.position']._get_fiscal_position(partner, delivery=shipping_partner)
        if fp:
            partner.property_account_position_id = fp
        create_values = {
            'partner_id': partner.id,
            'partner_shipping_id': shipping_partner.id,
            'state': 'draft',
            'client_order_ref': transaction['OrderLineItemID'],
            'origin': 'eBay' + transaction['OrderLineItemID'],
            'fiscal_position_id': fp.id,
            'date_order': product._ebay_parse_date(order['PaidTime']),
        }
        if self.env['ir.config_parameter'].sudo().get_param('ebay_sales_team'):
            create_values['team_id'] = int(
                self.env['ir.config_parameter'].sudo().get_param('ebay_sales_team'))

        sale_order = self.env['sale.order'].create(create_values)

        sale_order._process_order_new_transaction(transaction)

        sale_order._process_order_shipping(order)

        return sale_order

    def _process_order_new_find_partners(self, order):
        def _find_state():
            state = self.env['res.country.state'].search([
                ('code', '=', infos.get('StateOrProvince')),
                ('country_id', '=', shipping_data['country_id'])
            ], limit=1)
            if not state:
                state = self.env['res.country.state'].search([
                    ('name', '=', infos.get('StateOrProvince')),
                    ('country_id', '=', shipping_data['country_id'])
                ], limit=1)
            return state

        buyer_ebay_id = order['BuyerUserID']
        infos = order['ShippingAddress']

        partner = self.env['res.partner'].search([('ebay_id', '=', buyer_ebay_id)], limit=1)
        if not partner:
            partner = self.env['res.partner'].create({'name': buyer_ebay_id, 'ebay_id': buyer_ebay_id})
        partner_data = {
            'name': infos.get('Name'),
            'ebay_id': buyer_ebay_id,
            'ref': 'eBay',
        }
        email = order['TransactionArray']['Transaction'][0]['Buyer']['Email']
        # After 15 days eBay doesn't send the email anymore but 'Invalid Request'.
        if email != 'Invalid Request':
            partner_data['email'] = email
        # if we reuse an existing partner, addresses might already been set on it
        # so we hold the address data in a temporary dictionary to see if we need to create it or not
        shipping_data = {}
        info_to_extract = [('name', 'Name'), ('street', 'Street1'),
                           ('street2', 'Street2'), ('city', 'CityName'),
                           ('zip', 'PostalCode'), ('phone', 'Phone')]
        for (odoo_name, ebay_name) in info_to_extract:
            shipping_data[odoo_name] = infos.get(ebay_name, '')
        shipping_data['country_id'] = self.env['res.country'].search(
                [('code', '=', infos['Country'])], limit=1).id
        shipping_data['state_id'] = _find_state().id
        shipping_partner = partner._find_existing_address(shipping_data)
        if not shipping_partner:
            # if the partner already has an address we create a new child contact to hold it
            # otherwise we can directly set the new address on the partner
            if partner.street:
                contact_data = {'parent_id': partner.id, 'type': 'delivery'}
                shipping_partner = self.env['res.partner'].create({**shipping_data, **contact_data})
            else:
                partner.write(shipping_data)
                shipping_partner = partner
        partner.write(partner_data)

        return (partner, shipping_partner)

    @api.model
    def _process_all_taxes(self, tax_dict, price_unit):
        """If there is more than one product sold, price_unit should actually be the sum of all products;
           price_unit is given per product, whereas the tax amount is computed over the sum of all products.
        """
        tax_commands = []
        tax_list_or_dict = tax_dict.get('TaxDetails', [])  # returns a list if it contains more than one tax, directly returns the tax dict
        for tax in [tax_list_or_dict] if isinstance(tax_list_or_dict, dict) else tax_list_or_dict:
            tax_amount = float(tax['TaxAmount']['value'])
            tax_rate = 100 * tax_amount / (price_unit - tax_amount) if price_unit > tax_amount > 0 else 0
            tax_description = tax.get('TaxDescription', '')
            tax_id = self._handle_taxes(tax_amount, tax_rate, description=tax_description)
            if tax_id:
                tax_commands.append((4, tax_id.id))
        return tax_commands or False

    @api.model
    def _handle_taxes(self, amount, rate, description=''):
        """eBay use price-included taxes.
           We ignore 0% taxes to avoid useless clutter,
           but that could be changed if their presence is required.
        """
        company = self.env.company
        tax = False
        if amount > 0 and rate > 0:
            tax = self.env['account.tax'].with_context(active_test=False).sudo().search([
                *self.env['account.tax']._check_company_domain(company),
                ('amount', '=', rate),
                ('amount_type', '=', 'percent'),
                ('price_include', '=', True),
                ('type_tax_use', '=', 'sale')], limit=1)
            if not tax:
                tax = self.env['account.tax'].sudo().create({
                    'name': 'Tax %.4f %%' % rate,
                    'amount': rate,
                    'amount_type': 'percent',
                    'type_tax_use': 'sale',
                    'description': '%s (eBay)' % description,
                    'company_id': company.id,
                    'price_include': True,
                    'active': False,
                })
        return tax

    def _process_order_shipping(self, order):
        self.ensure_one()

        if 'ShippingServiceSelected' in order:
            shipping_cost_dict = order['ShippingServiceSelected']['ShippingServiceCost']
            shipping_amount = float(shipping_cost_dict['value'])
            shipping_currency = self.env['res.currency'].with_context(active_test=False).search(
                [('name', '=', shipping_cost_dict['_currencyID'])], limit=1)
            shipping_name = order['ShippingServiceSelected']['ShippingService']
            shipping_product = self.env['product.template'].search(
                [('name', '=', shipping_name)], limit=1)
            if not shipping_product:
                shipping_product = self.env['product.template'].create({
                    'name': shipping_name,
                    'type': 'service',
                    'categ_id': self.env.ref('sale_ebay.product_category_ebay').id,
                })
            tax_dict = order['ShippingDetails']['SalesTax']
            tax_amount = float(tax_dict.get('SalesTaxAmount', {}).get('value', 0))
            # the rate on the tax amount is actually on the product unit price, not on the shipping
            # and it's a tax not included in the price, contrarily to the product tax
            tax_rate = tax_dict.get('SalesTaxPercent', '0')
            tax_id = False
            if tax_amount:
                tax_id = self.env['account.tax'].sudo().create({
                    'name': tax_rate + '% Sales tax (eBay)',
                    'amount': tax_amount,
                    'amount_type': 'fixed',
                    'type_tax_use': 'sale',
                    'company_id': self.env.company.id,
                    'active': False,
                })

            price_unit = shipping_currency._convert(shipping_amount,
                self.currency_id, self.company_id, self.date_order or datetime.now())

            so_line = self.env['sale.order.line'].create({
                'order_id': self.id,
                'name': shipping_name,
                'product_id': shipping_product.product_variant_ids[0].id,
                'product_uom_qty': 1,
                'price_unit': price_unit,
                'tax_id': [(4, tax_id.id)] if tax_id else False,
                'is_delivery': True,
            })

    def _process_transaction_product(self, transaction):
        Template = self.env['product.template']
        ebay_id = transaction['Item']['ItemID']
        product = Template.search([('ebay_id', '=', ebay_id)], order='ebay_use desc', limit=1)
        if not product:
            product = Template.create({
                'name': transaction['Item']['Title'],
                'ebay_id': ebay_id,
                'ebay_use': True,
                'ebay_sync_stock': False,
            })
            product.message_post(body=
                _('Product created from eBay transaction %s', transaction['TransactionID']))

        if product.product_variant_count > 1:
            if 'Variation' in transaction:
                variant = product.product_variant_ids.filtered(
                    lambda l:
                    l.ebay_use and
                    l.ebay_variant_url.split("vti", 1)[1] ==
                    transaction['Variation']['VariationViewItemURL'].split("vti", 1)[1])
            # If multiple variants but only one listed on eBay as Item Specific
            else:
                call_data = {'ItemID': product.ebay_id, 'IncludeItemSpecifics': True}
                resp = product._ebay_execute('GetItem', call_data)
                name_value_list = resp.dict()['Item']['ItemSpecifics']['NameValueList']
                if not isinstance(name_value_list, list):
                    name_value_list = [name_value_list]
                # get only the item specific in the value list
                variant = product._get_variant_from_ebay_specs([n for n in name_value_list if n['Source'] == 'ItemSpecific'])
        else:
            variant = product.product_variant_ids[0]
        variant.ebay_quantity_sold = variant.ebay_quantity_sold + int(transaction['QuantityPurchased'])
        if not product.ebay_sync_stock:
            variant.ebay_quantity = variant.ebay_quantity - int(transaction['QuantityPurchased'])
            variant_qty = 0
            if len(product.product_variant_ids.filtered('ebay_use')) > 1:
                variant_qty = sum(product.product_variant_ids.mapped('ebay_quantity'))
            else:
                variant_qty = variant.ebay_quantity
            if variant_qty <= 0:
                if self.env['ir.config_parameter'].sudo().get_param('ebay_out_of_stock'):
                    product.ebay_listing_status = 'Out Of Stock'
                else:
                    product.ebay_listing_status = 'Ended'
        return product, variant

    def _process_order_new_transaction(self, transaction):
        self.ensure_one()

        product, variant = self._process_transaction_product(transaction)

        transaction_currency = self.env['res.currency'].with_context(active_test=False).search(
            [('name', '=', transaction['TransactionPrice']['_currencyID'])], limit=1)
        price_unit = float(transaction['TransactionPrice']['value'])
        price_unit = transaction_currency._convert(price_unit,
            self.currency_id, self.company_id, self.date_order or datetime.now())
        qty = float(transaction['QuantityPurchased'])
        tax_commands = self._process_all_taxes(transaction['Taxes'], price_unit * qty)

        sol = self.env['sale.order.line'].create({
            'product_id': variant.id,
            'order_id': self.id,
            'product_uom_qty': qty,
            'price_unit': price_unit,
            'tax_id': tax_commands,
        })

        if 'BuyerCheckoutMessage' in transaction:
            self.message_post(body=_('The Buyer Posted :\n') + transaction['BuyerCheckoutMessage'])

        self.env['product.template']._put_in_queue(product.id)

    def _process_order_update(self, order):
        self.ensure_one()

        product_lines = self.order_line.filtered(lambda l: not l._is_delivery())
        are_all_products_listed = all(product_lines.mapped('product_id.ebay_url'))
        can_be_invoiced = ('order' in product_lines.mapped('product_id.invoice_policy') and
                           'to invoice' in product_lines.mapped('invoice_status'))

        no_confirm = (self.env.context.get('ebay_no_confirm', False) or
                      not are_all_products_listed)
        try:
            if (not no_confirm and self.state in ['draft', 'sent']):
                self.action_confirm()
            if not no_confirm and can_be_invoiced:
                self._create_invoices()
            shipping_name = order['ShippingServiceSelected']['ShippingService']
            if self.picking_ids and shipping_name:
                self.picking_ids[-1].message_post(
                    body=_('The Buyer Chose The Following Delivery Method :\n') + shipping_name)
        except UserError as e:
            self.message_post(body=
                _('Ebay Synchronisation could not confirm because of the following error:\n%s', str)(e))

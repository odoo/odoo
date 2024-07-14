# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo import models, fields


class ebay_link_listing(models.TransientModel):
    _name = 'ebay.link.listing'
    _description = 'eBay Link Listing'

    ebay_id = fields.Char('eBay Listing ID')

    def link_listing(self):
        for listing in self:
            listing._link_listing()

    def _link_listing(self):
        response = self.env['product.template']._ebay_execute('GetItem', {
            'ItemID': self.ebay_id,
            'DetailLevel': 'ReturnAll'
        })
        item = response.dict()['Item']
        currency = self.env['res.currency'].search([
            ('name', '=', item['StartPrice']['_currencyID'])])
        product = self.env['product.template'].browse(self._context.get('active_id'))
        product_values = {
            'ebay_id': item['ItemID'],
            'ebay_url': item['ListingDetails']['ViewItemURL'],
            'ebay_listing_status': item['SellingStatus']['ListingStatus'],
            'ebay_title': item['Title'],
            'ebay_subtitle': item['SubTitle'] if 'SubTitle' in item else False,
            'ebay_description': item['Description'],
            'ebay_item_condition_id': self.env['ebay.item.condition'].search([
                ('code', '=', item['ConditionID'])
            ]).id if 'ConditionID' in item else False,
            'ebay_category_id': self.env['ebay.category'].search([
                ('category_id', '=', item['PrimaryCategory']['CategoryID']),
                ('category_type', '=', 'ebay')
            ]).id,
            'ebay_store_category_id': self.env['ebay.category'].search([
                ('category_id', '=', item['Storefront']['StoreCategoryID']),
                ('category_type', '=', 'store')
            ]).id if 'Storefront' in item else False,
            'ebay_store_category_2_id': self.env['ebay.category'].search([
                ('category_id', '=', item['Storefront']['StoreCategory2ID']),
                ('category_type', '=', 'store')
            ]).id if 'Storefront' in item else False,
            'ebay_price': currency._convert(
                float(item['StartPrice']['value']),
                self.env.company.currency_id,
                self.env.company,
                fields.Date.today()
            ),
            'ebay_buy_it_now_price': currency._convert(
                float(item['BuyItNowPrice']['value']),
                self.env.company.currency_id,
                self.env.company,
                fields.Date.today()
            ),
            'ebay_listing_type': item['ListingType'],
            'ebay_listing_duration': item['ListingDuration'],
            'ebay_best_offer': True if 'BestOfferDetails' in item
                and item['BestOfferDetails']['BestOfferEnabled'] == 'true' else False,
            'ebay_private_listing': True if item['PrivateListing'] == 'true' else False,
            'ebay_start_date': datetime.strptime(
                item['ListingDetails']['StartTime'].split('.')[0], '%Y-%m-%dT%H:%M:%S'),
            'ebay_last_sync': datetime.now(),
        }
        if 'SellerProfiles' in item:
            if 'SellerPaymentProfile' in item['SellerProfiles']\
                and 'PaymentProfileID' in item['SellerProfiles']['SellerPaymentProfile']:
                ebay_seller_payment_policy = self.env['ebay.policy'].search([
                    ('policy_type', '=', 'PAYMENT'),
                    ('policy_id', '=', item['SellerProfiles']['SellerPaymentProfile']['PaymentProfileID'])
                ], limit=1)
                if ebay_seller_payment_policy:
                    product_values['ebay_seller_payment_policy_id'] = ebay_seller_payment_policy.id
            if 'SellerReturnProfile' in item['SellerProfiles']\
                and 'ReturnProfileID' in item['SellerProfiles']['SellerReturnProfile']:
                ebay_seller_return_policy = self.env['ebay.policy'].search([
                    ('policy_type', '=', 'RETURN_POLICY'),
                    ('policy_id', '=', item['SellerProfiles']['SellerReturnProfile']['ReturnProfileID'])
                ], limit=1)
                if ebay_seller_return_policy:
                    product_values['ebay_seller_return_policy_id'] = ebay_seller_return_policy.id
            if 'SellerShippingProfile' in item['SellerProfiles']\
                and 'ShippingProfileID' in item['SellerProfiles']['SellerShippingProfile']:
                ebay_seller_shipping_policy = self.env['ebay.policy'].search([
                    ('policy_type', '=', 'SHIPPING'),
                    ('policy_id', '=', item['SellerProfiles']['SellerShippingProfile']['ShippingProfileID'])
                ], limit=1)
                if ebay_seller_shipping_policy:
                    product_values['ebay_seller_shipping_policy_id'] = ebay_seller_shipping_policy.id
        product.write(product_values)

        if 'Variations' in item:
            variations = item['Variations']['Variation']
            if not isinstance(variations, list):
                variations = [variations]
            for variation in variations:
                specs = variation['VariationSpecifics']['NameValueList']
                if not isinstance(specs, list):
                    specs = [specs]
                variant = product._get_variant_from_ebay_specs(specs)
                variant.write({
                    'ebay_use': True,
                    'ebay_quantity_sold': variation['SellingStatus']['QuantitySold'],
                    'ebay_fixed_price': currency._convert(
                        float(variation['StartPrice']['value']),
                        self.env.company.currency_id,
                        self.env.company,
                        fields.Date.today()
                    ),
                    'ebay_quantity': int(variation['Quantity']) - int(variation['SellingStatus']['QuantitySold']),
                })
            product._set_variant_url(self.ebay_id)
        elif product.product_variant_count == 1:
            product.product_variant_ids.write({
                'ebay_quantity_sold': item['SellingStatus']['QuantitySold'],
                'ebay_fixed_price': currency._convert(
                    float(item['StartPrice']['value']),
                    self.env.company.currency_id,
                    self.env.company,
                    fields.Date.today()
                ),
                'ebay_quantity': int(item['Quantity']) - int(item['SellingStatus']['QuantitySold']),
            })

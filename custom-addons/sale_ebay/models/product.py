# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import io
import re
import logging
from PIL import Image

from datetime import datetime, timedelta
from markupsafe import Markup
from xml.sax.saxutils import escape

from odoo import models, fields, api, _
from odoo.exceptions import UserError, RedirectWarning, ValidationError
from odoo.tools import check_barcode_encoding
from odoo.osv import expression

from odoo.addons.sale_ebay.tools.ebaysdk import EbayConnection, EbayConnectionError

_logger = logging.getLogger(__name__)

_30DAYS = timedelta(days=30)
EBAY_DATEFORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'


def _ebay_parse_date(s):  # should be fromisoformat starting with datetime 3.7
    return datetime.strptime(s, EBAY_DATEFORMAT)


def _log_logging(env, message, function_name, path):
    env['ir.logging'].sudo().create({
        'name': 'eBay',
        'type': 'server',
        'level': 'DEBUG',
        'dbname': env.cr.dbname,
        'message': message,
        'func': function_name,
        'path': path,
        'line': '0',
    })

class ProductTemplate(models.Model):
    _inherit = "product.template"

    ebay_id = fields.Char('eBay ID', copy=False)
    ebay_use = fields.Boolean('Use eBay', default=False)
    ebay_url = fields.Char('eBay url', readonly=True, copy=False)
    ebay_listing_status = fields.Char('eBay Status', default='Unlisted', readonly=True, copy=False)
    ebay_title = fields.Char('Title', size=80,
        help='The title is restricted to 80 characters')
    ebay_subtitle = fields.Char('Subtitle', size=55,
        help='The subtitle is restricted to 55 characters. Fees can be claimed by eBay for this feature')
    ebay_description = fields.Html('eBay Description', default='<p><br></p>')
    ebay_item_condition_id = fields.Many2one('ebay.item.condition', string="Item Condition")
    ebay_category_id = fields.Many2one('ebay.category',
        string="Category", domain=[('category_type', '=', 'ebay'),('leaf_category','=',True)])
    ebay_category_2_id = fields.Many2one('ebay.category',
        string="Category 2 (Optional)", domain=[('category_type', '=', 'ebay'),('leaf_category','=',True)],
        help="The use of a secondary category is not allowed on every eBay sites. Fees can be claimed by eBay for this feature")
    ebay_store_category_id = fields.Many2one('ebay.category',
        string="Store Category (Optional)", domain=[('category_type', '=', 'store'),('leaf_category','=',True)])
    ebay_store_category_2_id = fields.Many2one('ebay.category',
        string="Store Category 2 (Optional)", domain=[('category_type', '=', 'store'),('leaf_category','=',True)])
    ebay_price = fields.Float(string='Starting Price for Auction')
    ebay_buy_it_now_price = fields.Float(string='Buy It Now Price')
    ebay_listing_type = fields.Selection([
        ('Chinese', 'Auction'),
        ('FixedPriceItem', 'Fixed price')], string='Listing Type', default='Chinese')
    ebay_listing_duration = fields.Selection([
        ('Days_3', '3 Days'),
        ('Days_5', '5 Days'),
        ('Days_7', '7 Days'),
        ('Days_10', '10 Days'),
        ('Days_30', '30 Days (only for fixed price)'),
        ('GTC', 'Good \'Til Cancelled (only for fixed price)')],
        string='Duration', default='Days_7')
    ebay_seller_payment_policy_id = fields.Many2one('ebay.policy',
        string="Payment Policy", domain=[('policy_type', '=', 'PAYMENT')])
    ebay_seller_return_policy_id = fields.Many2one('ebay.policy',
        string="Return Policy", domain=[('policy_type', '=', 'RETURN_POLICY')])
    ebay_seller_shipping_policy_id = fields.Many2one('ebay.policy',
        string="Shipping Policy", domain=[('policy_type', '=', 'SHIPPING')])
    ebay_sync_stock = fields.Boolean(string="Use Stock Quantity", default=False)
    ebay_best_offer = fields.Boolean(string="Allow Best Offer", default=False)
    ebay_private_listing = fields.Boolean(string="Private Listing", default=False)
    ebay_start_date = fields.Datetime('Start Date', readonly=True, copy=False)
    ebay_quantity_sold = fields.Integer(related='product_variant_ids.ebay_quantity_sold', store=True, readonly=False, copy=False)
    ebay_fixed_price = fields.Float(related='product_variant_ids.ebay_fixed_price', store=True, readonly=False)
    ebay_quantity = fields.Integer(related='product_variant_ids.ebay_quantity', store=True, readonly=False, default=1)
    ebay_last_sync = fields.Datetime(string="Last update", copy=False)
    ebay_template_id = fields.Many2one('mail.template', string='Description Template',
        ondelete='set null')

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)
        related_fields = ['ebay_fixed_price', 'ebay_quantity']
        for product, vals in zip(products, vals_list):
            related_values = {}
            for field in related_fields:
                if vals.get(field):
                    related_values[field] = vals[field]
            if related_values:
                product.write(related_values)
        return products

    def _prepare_item_dict(self):
        if self.ebay_sync_stock:
            self.ebay_quantity = max(int(self.virtual_available), 0)
        country_id = self.env['ir.config_parameter'].sudo().get_param('ebay_country')
        country = self.env['res.country'].browse(int(country_id))
        currency_id = self.env['ir.config_parameter'].sudo().get_param('ebay_currency')
        currency = self.env['res.currency'].browse(int(currency_id))
        comp_currency = self.env.company.currency_id
        item = {
            "Item": {
                "Title": self._ebay_encode(self.ebay_title),
                "PrimaryCategory": {"CategoryID": self.ebay_category_id.category_id},
                "StartPrice": comp_currency._convert(self.ebay_price, currency, self.env.company, fields.Date.today())
                if self.ebay_listing_type == 'Chinese'
                else comp_currency._convert(self.ebay_fixed_price, currency, self.env.company, fields.Date.today()),
                "CategoryMappingAllowed": "true",
                "Country": country.code,
                "Currency": currency.name,
                "ConditionID": self.ebay_item_condition_id.code,
                "ListingDuration": self.ebay_listing_duration,
                "ListingType": self.ebay_listing_type,
                "PostalCode": self.env['ir.config_parameter'].sudo().get_param('ebay_zip_code'),
                "Location": self.env['ir.config_parameter'].sudo().get_param('ebay_location'),
                "Quantity": self.ebay_quantity,
                "BestOfferDetails": {'BestOfferEnabled': self.ebay_best_offer},
                "PrivateListing": self.ebay_private_listing,
                "SellerProfiles": {
                    "SellerPaymentProfile": {
                        "PaymentProfileID": self.ebay_seller_payment_policy_id.policy_id,
                    },
                    "SellerReturnProfile": {
                        "ReturnProfileID": self.ebay_seller_return_policy_id.policy_id,
                    },
                    "SellerShippingProfile": {
                        "ShippingProfileID": self.ebay_seller_shipping_policy_id.policy_id,
                    }
                },
            }
        }
        if self.ebay_description and self.ebay_template_id:
            description = self.ebay_template_id._render_field('body_html', self.ids)[self.id]
            item['Item']['Description'] = Markup('<![CDATA[{0}]]>').format(description)
        if self.ebay_subtitle:
            item['Item']['SubTitle'] = self._ebay_encode(self.ebay_subtitle)
        picture_urls = self._create_picture_url()
        if picture_urls:
            item['Item']['PictureDetails'] = {'PictureURL': picture_urls}
            if self.env['ir.config_parameter'].sudo().get_param('ebay_gallery_plus'):
                item['Item']['PictureDetails']['GalleryType'] = 'Plus'
        if self.ebay_listing_type == 'Chinese' and self.ebay_buy_it_now_price:
            item['Item']['BuyItNowPrice'] = comp_currency._convert(self.ebay_buy_it_now_price, currency, self.env.company, fields.Date.today())
        NameValueList = []
        variant = self.product_variant_ids.filtered('ebay_use')
        # We set by default the brand and the MPN because of the new eBay policy
        # That make them mandatory in most category
        item['Item']['ProductListingDetails'] = {'BrandMPN': {'Brand': 'Unbranded'}}
        item['Item']['ProductListingDetails']['BrandMPN']['MPN'] = 'Does not Apply'
        # If only one variant selected to be published, we don't create variant
        # but set the variant's value has an item specific on eBay
        if len(variant) == 1 \
           and self.ebay_listing_type == 'FixedPriceItem':
            if self.ebay_sync_stock:
                variant.ebay_quantity = max(int(variant.virtual_available), 0)
            item['Item']['Quantity'] = variant.ebay_quantity
            item['Item']['StartPrice'] = variant.ebay_fixed_price
        # We use the attribute to set the attributes linked to computed shipping policies
        # We don't use attributes since this fix has been done in stable release but will be done
        # in master.
        # We don't use the weight attribute due to the fact that eBay handles the English system
        # of measurement which uses Lbs and Oz. Then we cannot just split the weight field.
        ShippingPackageAttributes = [
            'PackageDepth', 'PackageLength', 'PackageWidth', 'WeightMajor',
            'WeightMinor', 'ShippingIrregular', 'ShippingPackage'
        ]
        # If one attribute has only one value, we don't create variant
        # but set the value has an item specific on eBay
        if self.attribute_line_ids:
            for attribute in self.attribute_line_ids:
                if len(attribute.value_ids) == 1:
                    attr_name = attribute.attribute_id.name
                    attr_value = self._ebay_encode(attribute.value_ids.name)
                    # We used the attributes in Odoo to match the Brand and MPN attributes
                    # But since 1st March 2016, eBay separated them from the other attributes
                    if attr_name == 'Brand':
                        item['Item']['ProductListingDetails']['BrandMPN']['Brand'] = attr_value
                    elif attr_name == 'MPN':
                        item['Item']['ProductListingDetails']['BrandMPN']['MPN'] = attr_value
                    elif attr_name in ShippingPackageAttributes:
                        if 'ShippingPackageDetails' not in item['Item']:
                            item['Item']['ShippingPackageDetails'] = {}
                        item['Item']['ShippingPackageDetails'][self._ebay_encode(attr_name)] = attr_value
                    else:
                        NameValueList.append({
                            'Name': self._ebay_encode(attr_name),
                            'Value': attr_value,
                        })

        # We add the Brand and the MPN at the end of the loop
        # because these attributes are mandatory since 1st March 2016
        # but some eBay site are not taking into account the ProductListingDetails.
        # This avoid to loop in the NameValueList array to ensure that it contains
        # Brand and MPN attributes
        brand_mpn = [
            {'Name': 'Brand',
             'Value': item['Item']['ProductListingDetails']['BrandMPN']['Brand']},
            {'Name': 'MPN',
             'Value': item['Item']['ProductListingDetails']['BrandMPN']['MPN']}
        ]
        NameValueList += brand_mpn
        if NameValueList:
            item['Item']['ItemSpecifics'] = {'NameValueList': NameValueList}
        if self.ebay_category_2_id:
            item['Item']['SecondaryCategory'] = {'CategoryID': self.ebay_category_2_id.category_id}
        if self.ebay_store_category_id:
            item['Item']['Storefront'] = {
                'StoreCategoryID': self.ebay_store_category_id.category_id,
                'StoreCategoryName': self._ebay_encode(self.ebay_store_category_id.name),
            }
            if self.ebay_store_category_2_id:
                item['Item']['Storefront']['StoreCategory2ID'] = self.ebay_store_category_2_id.category_id
                item['Item']['Storefront']['StoreCategory2Name'] = self._ebay_encode(self.ebay_store_category_2_id.name)
        return item

    @api.model
    def _ebay_encode(self, string):
        return escape(string.strip()) if string else ''

    def _prepare_non_variant_dict(self):
        item = self._prepare_item_dict()
        # Set default value to UPC
        item['Item']['ProductListingDetails']['UPC'] = 'Does not Apply'
        # Check the length of the barcode field to guess its type.
        if self.barcode:
            if check_barcode_encoding(self.barcode, 'upca'):
                item['Item']['ProductListingDetails']['UPC'] = self.barcode
            elif check_barcode_encoding(self.barcode, 'ean13'):
                item['Item']['ProductListingDetails']['EAN'] = self.barcode
        return item

    def _prepare_variant_dict(self):
        if not self.product_variant_ids.filtered('ebay_use'):
            raise UserError(_("Error Encountered.\n No Variant Set To Be Listed On eBay."))
        currency_id = self.env['ir.config_parameter'].sudo().get_param('ebay_currency')
        currency = self.env['res.currency'].browse(int(currency_id))
        comp_currency = self.env.company.currency_id
        items = self._prepare_item_dict()
        items['Item']['Variations'] = {
            'Variation': [],
            'VariationSpecificsSet': self._get_ebay_variation_specific_set(),
        }
        variations = items['Item']['Variations']['Variation']

        for variant in self.product_variant_ids:
            if self.ebay_sync_stock:
                variant.ebay_quantity = max(int(variant.virtual_available), 0)
            if variant.ebay_use and not variant.ebay_quantity and\
               not self.env['ir.config_parameter'].sudo().get_param('ebay_out_of_stock'):
                raise UserError(_('All the quantities must be greater than 0 or you need to enable the Out Of Stock option.'))
            # Since 1st March 2016, identifiers are mandatory
            # We set default values in case none is set by the user
            # Check the length of the barcode field to guess its type.
            upc = 'Does not apply'
            ean = 'Does not apply'
            if variant.barcode:
                if check_barcode_encoding(variant.barcode, 'upca'):
                    upc = variant.barcode
                elif check_barcode_encoding(variant.barcode, 'ean13'):
                    ean = variant.barcode
            variations.append({
                'Quantity': variant.ebay_quantity,
                'StartPrice': comp_currency._convert(variant.ebay_fixed_price, currency, self.env.company, fields.Date.today()),
                'VariationSpecifics': variant._get_ebay_variation_specifics(),
                'Delete': False if variant.ebay_use else True,
                'VariationProductListingDetails': {
                    'UPC': upc,
                    'EAN': ean,
                },
            })
        return items

    def _get_item_dict(self):
        self.ensure_one()
        if len(self.product_variant_ids) > 1 and self.ebay_listing_type == 'FixedPriceItem':
            item_dict = self._prepare_variant_dict()
        else:
            item_dict = self._prepare_non_variant_dict()
        return item_dict

    def _set_variant_url(self, item_id):
        self.ensure_one()
        variants = self.product_variant_ids.filtered('ebay_use')
        if len(variants) > 1 and self.ebay_listing_type == 'FixedPriceItem':
            for variant in variants:
                call_data = {
                    'ItemID': item_id,
                    'VariationSpecifics': variant._get_ebay_variation_specifics(),
                }
                item = self._ebay_execute('GetItem', call_data)
                variant.ebay_variant_url = item.dict()['Item']['ListingDetails']['ViewItemURL']

    @api.model
    def _ebay_configured(self):
        return bool(self._get_ebay_params())

    @api.model
    def _get_ebay_params(self):
        params = self.env['ir.config_parameter'].sudo()
        domain = params.get_param('ebay_domain')
        if domain == 'sand':
            app_id = params.get_param('ebay_sandbox_app_id')
            cert_id = params.get_param('ebay_sandbox_cert_id')
            token = params.get_param('ebay_sandbox_token')
            domain = 'api.sandbox.ebay.com'
        else:
            app_id = params.get_param('ebay_prod_app_id')
            cert_id = params.get_param('ebay_prod_cert_id')
            token = params.get_param('ebay_prod_token')
            domain = 'api.ebay.com'

        if not app_id or not cert_id or not token:
            return {}

        dev_id = params.get_param('ebay_dev_id')
        site_id = params.get_param('ebay_site')
        site = self.env['ebay.site'].browse(int(site_id))
        return dict(
            domain=domain,
            appid=app_id,
            certid=cert_id,
            token=token,
            siteid=site.ebay_id,
            devid=dev_id,
            config_file=None,
        )

    @api.model
    def _get_ebay_api(self):
        params = self._get_ebay_params()

        if not params:
            action = self.env.ref('sale.action_sale_config_settings')
            raise RedirectWarning(_('One parameter is missing.'),
                                  action.id, _('Configure The eBay Integrator Now'))

        return EbayConnection(**params)

    @api.model
    def _ebay_execute(self, verb, data=None, list_nodes=[], verb_attrs=None, files=None):
        ebay_api = self._get_ebay_api()
        try:
            return ebay_api.execute(verb, data, list_nodes, verb_attrs, files)
        except EbayConnectionError as e:
            errors = e.response.dict()['Errors']
            if not isinstance(errors, list):
                errors = [errors]
            error_message = ''
            for error in errors:
                if error['SeverityCode'] == 'Error':
                    error_message += error['LongMessage'] + '(' + error['ErrorCode'] + ')'
            if error['ErrorCode'] == '21916884':
                error_message += _('Or the condition is not compatible with the category.')
            if error['ErrorCode'] == '10007' or error['ErrorCode'] == '21916803':
                error_message = _('eBay is unreachable. Please try again later.')
            if error['ErrorCode'] == '21916635':
                error_message = _('Impossible to revise a listing into a multi-variations listing.\n Create a new listing.')
            if error['ErrorCode'] == '942':
                error_message += _(" If you want to set quantity to 0, the Out Of Stock option should be enabled"
                                   " and the listing duration should set to Good 'Til Canceled")
            if error['ErrorCode'] == '21916626':
                error_message = _(" You need to have at least 2 variations selected for a multi-variations listing.\n"
                                  " Or if you try to delete a variation, you cannot do it by unselecting it."
                                  " Setting the quantity to 0 is the safest method to make a variation unavailable.")
            raise UserError(_("Error Encountered.\n%r", error_message))

    def _get_ebay_images_attachments(self):
        """Images need to follow some guidelines to be accepted on ebay, otherwise they may generate errors
           https://developer.ebay.com/DevZone/guides/features-guide/default.html#development/Pictures-Intro.html
           https://developer.ebay.com/devzone/xml/docs/Reference/eBay/types/PictureDetailsType.html

        :return: all attachments that are images satisfying ebay requirements
        """
        self.ensure_one()
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'product.template'),
            ('res_id', '=', self.id),
            ('mimetype', 'ilike', 'image'),
        ], order="create_date")

        def is_good_image(att):
            try:
                data = io.BytesIO(base64.standard_b64decode(att["datas"]))
                img = Image.open(data)
                good_image = (max(img.size) >= 500 and
                              sum(img.size) <= 12000 and
                              data.getbuffer().nbytes <= 12e6 and
                              (not img.format == 'JPEG' or img.mode == 'RGB'))
                return good_image
            except Exception as e:
                return False

        return attachments.filtered(lambda a: is_good_image(a))[:12]

    def _create_picture_url(self):
        attachments = self._get_ebay_images_attachments()

        urls = []
        for att in attachments:
            image = io.BytesIO(base64.standard_b64decode(att["datas"]))
            files = {'file': ('EbayImage', image)}
            pictureData = {
                "WarningLevel": "High",
                "PictureName": self.name
            }
            response = self._ebay_execute('UploadSiteHostedPictures', pictureData, files=files)
            urls.append(response.dict()['SiteHostedPictureDetails']['FullURL'])
        return urls

    def _update_ebay_data(self, response):
        item = self._ebay_execute('GetItem', {'ItemID': response['ItemID']}).dict()
        qty = int(item['Item']['Quantity']) - int(item['Item']['SellingStatus']['QuantitySold'])
        for product in self:
            product.write({
                'ebay_listing_status': 'Active' if qty > 0 else 'Out Of Stock',
                'ebay_id': response['ItemID'],
                'ebay_url': item['Item']['ListingDetails']['ViewItemURL'],
                'ebay_start_date': _ebay_parse_date(response['StartTime']),
            })

    def push_product_ebay(self):
        for product in self:
            if product.ebay_listing_status != 'Active':
                item_dict = product._get_item_dict()

                response = self._ebay_execute('AddItem' if product.ebay_listing_type == 'Chinese'
                                             else 'AddFixedPriceItem', item_dict)
                product._set_variant_url(response.dict()['ItemID'])
                product._update_ebay_data(response.dict())

    def end_listing_product_ebay(self):
        for product in self:
            call_data = {"ItemID": product.ebay_id,
                         "EndingReason": "NotAvailable"}
            self._ebay_execute('EndItem' if product.ebay_listing_type == 'Chinese'
                              else 'EndFixedPriceItem', call_data)
            product.ebay_listing_status = 'Ended'

    def relist_product_ebay(self):
        for product in self:
            item_dict = product._get_item_dict()
            # set the item id to relist the correct ebay listing
            item_dict['Item']['ItemID'] = product.ebay_id
            response = self._ebay_execute('RelistItem' if product.ebay_listing_type == 'Chinese'
                                         else 'RelistFixedPriceItem', item_dict)
            product._set_variant_url(response.dict()['ItemID'])
            product._update_ebay_data(response.dict())

    def revise_product_ebay(self):
        for product in self:
            item_dict = product._get_item_dict()
            # set the item id to revise the correct ebay listing
            item_dict['Item']['ItemID'] = product.ebay_id
            if not product.ebay_subtitle:
                item_dict['DeletedField'] = 'Item.SubTitle'

            response = self._ebay_execute('ReviseItem' if product.ebay_listing_type == 'Chinese'
                                         else 'ReviseFixedPriceItem', item_dict)
            product._set_variant_url(response.dict()['ItemID'])
            product._update_ebay_data(response.dict())

    @api.model
    def process_queue(self):
        queue_str = self.env['ir.config_parameter'].sudo().get_param('ebay_queue')
        queue = [int(s) for s in queue_str.split(',')] if queue_str else []
        process_next_time = []
        Product = self.env['product.template']
        for template_id in queue:
            template = Product.browse(template_id).exists()
            if template:
                try:
                    template.sync_available_qty()
                except Exception as e:
                    _log_logging(self.env, str(e), "process_queue", template_id)
                    process_next_time.append(template_id)
        new_queue = ','.join([str(n) for n in process_next_time])
        self.env['ir.config_parameter'].sudo().set_param('ebay_queue', new_queue)

    def _put_in_queue(self, value):
        queue_str = self.env['ir.config_parameter'].sudo().get_param('ebay_queue')
        queue = set(queue_str.split(',')) if queue_str else set()
        queue.add(str(value))
        new_queue_str = ','.join(queue)
        self.env['ir.config_parameter'].sudo().set_param('ebay_queue', new_queue_str)

    def synchronize_orders_from_last_sync(self, test_mode=False):
        """
        Get all eBay orders since the parameter 'ebay_last_sync'.
        Note that all datetimes are considered in UTC.
        """
        if not self._ebay_configured():
            return
        now = datetime.now()
        last_sync_str = self.env['ir.config_parameter'].sudo().get_param('ebay_last_sync')
        if not last_sync_str:
            raise UserError(_(
                'There is no last synchronization date in your System Parameters. '
                'Create a System Parameter record with the key "ebay_last_sync" '
                'and the value set to the date of the oldest order you wish to synchronize '
                'in the format "YYYY-MM-DD".'))
        last_sync = fields.Datetime.from_string(last_sync_str)
        success = self.synchronize_orders(last_sync)
        if success:
            # https://ebaydts.com/eBayKBDetails?KBid=1788
            # Set time to the current time minus 2 minutes, in case there is a gap in server response
            new_sync = fields.Datetime.to_string(now - timedelta(minutes=2))
            self.env['ir.config_parameter'].sudo().set_param('ebay_last_sync', new_sync)
        if not test_mode:
            self.process_queue()

    def _ebay_ranges(self, date_from, date_to):
        """
        ebay does not allow to synchronize ranges of more than 30 days.
        If we need to synchronize something for a greater range, we need to split it.
        :param date_from: date(time)
        :param date_to: date(time)
        :return: [(date_from, date_to)*] where each couple is less than 30 days apart
        """
        if date_to - date_from <= _30DAYS:
            return [(date_from, date_to)]
        else:
            step = date_from + _30DAYS
            return [(date_from, step)] + self._ebay_ranges(step, date_to)

    @api.model
    def synchronize_orders_recovery(self, date_from_str, date_to_str):
        """
            Dates should be in format YYYY-MM-DD, and in UTC.
            The context key 'no_confirm' is added so that recovered orders stay as quotation.
        """
        self = self.with_context(no_confirm=True)
        date_from = fields.Datetime.from_string(date_from_str)
        date_to = fields.Datetime.from_string(date_to_str)
        return self.synchronize_orders(date_from, date_to)

    @api.model
    def synchronize_orders(self, date_from, date_to=False):
        """
        :param date_from: date(time) object
        :param date_to: date(time) object
        :return: boolean: did sync succeed?
        """
        if not date_to:
            date_to = datetime.now()
        ranges = self._ebay_ranges(date_from, date_to)
        successes = [
            self._synchronize_orders_ranged(dt_from, dt_to)
            for (dt_from, dt_to) in ranges
        ]
        return all(successes)

    def _synchronize_orders_ranged(self, date_from, date_to, page=1):
        """
        ebay does not allow to synchronize ranges of more than 30 days.
        It will crash if given dates that aren't good, use _ebay_ranges.
        :param date_from: datetime
        :param date_to: datetime
        :return: bool (did synchronisation succeed)
        """
        if not date_to - date_from <= _30DAYS:
            raise ValidationError(_("This function should not be called with a range of more than 30 days, "
                                  "as eBay does not handle longer timespans. "
                                  "Instead use synchronize_orders which split in as many calls as needed."))
        call_data = {
            'ModTimeFrom': str(date_from),
            'ModTimeTo': str(date_to),
            'Pagination': {'EntriesPerPage': 100,  # max allowed by ebay
                           'PageNumber': page,
                           }
        }
        try:
            response = self._ebay_execute('GetOrders', call_data)
            order_dict = response.dict()
            if int(order_dict['ReturnedOrderCountActual']) > 0:  # order_dict.get('OrderArray'):
                for order in order_dict['OrderArray']['Order']:
                    # https://ebaydts.com/eBayKBDetails?KBid=1788: If Checkout is not Complete,
                    # then the transaction is not completely ready for post sales processing
                    if order['CheckoutStatus']['Status'] == 'Complete':
                        self.env['sale.order']._process_order(order)
            if int(order_dict['PaginationResult']['TotalNumberOfPages']) > page:
                self._synchronize_orders_ranged(date_from, date_to, page=page+1)
        except Exception as e:
            message = "Ebay synchronization exception:\n%s" % str(e)
            path = ", ".join(str(param) for param in [date_from, date_to, page])
            _log_logging(self.env, message, "_synchronize_orders_ranged", path)
            _logger.exception(message)
            return False
        return True

    def sync_available_qty(self):
        for product in self:
            product._sync_available_qty()

    def _sync_available_qty(self):
        if self.ebay_sync_stock:
            if self.ebay_listing_status in ['Active', 'Error']:
                # The product is Active on eBay but there is no more stock
                if self.virtual_available <= 0:
                    # Only revise product if there is a change of quantity
                    if len(self.product_variant_ids.filtered('ebay_use')) > 1:
                        for variant in self.product_variant_ids:
                            if variant.virtual_available != variant.ebay_quantity:
                                # If the Out Of Stock option is enabled only need to revise the quantity
                                if self.env['ir.config_parameter'].sudo().get_param('ebay_out_of_stock'):
                                    self.revise_product_ebay()
                                    self.ebay_listing_status = 'Out Of Stock'
                                else:
                                    self.end_listing_product_ebay()
                                    self.ebay_listing_status = 'Ended'
                    elif self.ebay_quantity != self.virtual_available:
                        # If the Out Of Stock option is enabled only need to revise the quantity
                        if self.env['ir.config_parameter'].sudo().get_param('ebay_out_of_stock'):
                            self.revise_product_ebay()
                            self.ebay_listing_status = 'Out Of Stock'
                        else:
                            self.end_listing_product_ebay()
                            self.ebay_listing_status = 'Ended'
                # The product is Active on eBay and there is some stock
                # Check if the quantity in Odoo is different than the one on eBay
                # If it is the case revise the quantity
                else:
                    if len(self.product_variant_ids.filtered('ebay_use')) > 1:
                        for variant in self.product_variant_ids:
                            if variant.virtual_available != variant.ebay_quantity:
                                self.revise_product_ebay()
                                break
                    else:
                        if self.ebay_quantity != self.virtual_available:
                            self.revise_product_ebay()
            elif self.ebay_listing_status == 'Out Of Stock':
                # The product is Out Of Stock on eBay but there is stock in Odoo
                # If the Out Of Stock option is enabled then only revise the product
                if self.virtual_available > 0 and self.ebay_quantity != self.virtual_available:
                    if self.env['ir.config_parameter'].sudo().get_param('ebay_out_of_stock'):
                        self.revise_product_ebay()
                    else:
                        self.relist_product_ebay()

    def unlink_listing_product_ebay(self):
        for product in self:
            product.write({
                'ebay_use': False,
                'ebay_id': False,
                'ebay_listing_status': 'Unlisted',
                'ebay_url': False,
            })

    def _get_ebay_variation_specific_set(self):
        self.ensure_one()
        # example of a valid name value list array
        # [{'Name':'size','Value':['16gb','32gb']},{'Name':'color', 'Value':['red','blue']}]
        return {
            'NameValueList': [{
                'Name': self._ebay_encode(ptal.attribute_id.name),
                'Value': [self._ebay_encode(ptav.product_attribute_value_id.name) for ptav in ptal.product_template_value_ids],
            } for ptal in self.valid_product_template_attribute_line_ids._without_no_variant_attributes()],
        }

    def _get_variant_from_ebay_specs(self, specs):
        """`specs` format is [{'Name': "...", 'Value': "..."}, ...]"""
        self.ensure_one()
        domain = expression.OR([[('attribute_id.name', '=', spec['Name']), ('product_attribute_value_id.name', '=', spec['Value'])] for spec in specs])
        combination = self.env['product.template.attribute.value'].search([('product_tmpl_id', '=', self.id)] + domain)
        return self._get_variant_for_combination(combination)


class ProductProduct(models.Model):
    _inherit = "product.product"

    ebay_use = fields.Boolean('Publish On eBay', default=False)
    ebay_quantity_sold = fields.Integer('Quantity Sold', readonly=True)
    ebay_fixed_price = fields.Float('eBay Fixed Price')
    ebay_quantity = fields.Integer(string='Quantity On eBay', default=1)
    ebay_listing_type = fields.Selection(related='product_tmpl_id.ebay_listing_type', readonly=False)
    ebay_variant_url = fields.Char('eBay Variant URL')

    def _get_ebay_variation_specifics(self):
        self.ensure_one()
        return {
            'NameValueList': [{
                'Name': self.env['product.template']._ebay_encode(ptav.attribute_id.name),
                'Value': self.env['product.template']._ebay_encode(ptav.product_attribute_value_id.name),
            } for ptav in self.product_template_attribute_value_ids._filter_single_value_lines()]
        }

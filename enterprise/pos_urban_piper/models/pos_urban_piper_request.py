import logging
import requests
import json

from datetime import datetime

from odoo import Command
from odoo.tools import html2plaintext

from urllib.parse import quote
from werkzeug.urls import url_join

_logger = logging.getLogger(__name__)

EVENT_TYPES = [
    'store_creation', 'store_action', 'inventory_update', 'item_state_toggle', 'order_placed', 'order_status_update', 'rider_status_update'
]
UP_LANGUAGES = ['hi', 'ar', 'ja', 'pt', 'fr', 'es']


class UrbanPiperClient:

    def __init__(self, config):
        """
        Initial parameters for making api requests.
        """
        self.config = config
        self.session = requests.Session()
        self.db_uuid = self.config.env['ir.config_parameter'].sudo().get_param('database.uuid')

    def _make_api_request(self, endpoint, method='POST', data=None, timeout=10):
        """
        Make an api call, return response for multiple api requests of urban piper.
        """
        user_name = self.config.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.urbanpiper_username')
        api_key = self.config.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.urbanpiper_apikey')
        headers = {
            'Authorization': f'apikey {user_name}:{api_key}',
            'Content-Type': 'application/json'
        }
        urbanpiper_url = 'https://pos-int.urbanpiper.com/' if self.config.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.is_production_mode') == 'False' else 'https://api.urbanpiper.com/'
        access_url = urbanpiper_url + endpoint
        try:
            # Make the API request
            response = self.session.request(method, access_url, json=data, headers=headers, timeout=timeout)
            # Parse the response as JSON
            response_json = response.json()
            # raise an error if the response is not successful
            response.raise_for_status()
            return response_json
        except requests.exceptions.ConnectionError as error:
            _logger.warning('Connection Error: %r with the given URL %r', error, access_url)
            return {'errors': {'timeout': 'Cannot reach the server. Please try again later.'}}
        except requests.exceptions.HTTPError as error:
            message = response_json.get("message")
            _logger.warning('HTTPError: %r', message or error)
            return {'errors': {'HTTPError': message or str(error)}}
        except json.decoder.JSONDecodeError as error:
            _logger.warning('JSONDecodeError: %r', error)
            return {'errors': {'JSONDecodeError': 'Failed to parse server response.'}}

    def configure_webhook(self):
        """
        Check and register webhook if the base url is changed.
        """
        base_url = self.config.get_base_url()
        if base_url != self.config.urbanpiper_webhook_url:
            self.config.urbanpiper_webhook_url = base_url
            self._register_webhook()

    def _register_webhook(self):
        """
        Register webhook on Atlas for get notified for order updates.
        """
        endpoint = 'external/api/v1/webhooks/'
        base_url = self.config.urbanpiper_webhook_url
        webhook_url = url_join(base_url, '/urbanpiper/webhook/')
        for event_type in EVENT_TYPES:
            controller_url = url_join(webhook_url, event_type)
            payload = {
                'active': True,
                'event_type': event_type,
                'retrial_interval_units': 'seconds',
                'url': controller_url,
                'headers': {
                    'X-Urbanpiper-Uuid': self.config.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.uuid')
                }
            }
            self._make_api_request(endpoint, data=payload)

    def request_store_create(self):
        """
        Request to create a store in UrbanPiper.
        """
        endpoint = 'external/api/v1/stores/'
        data = {
            'stores': [
                {
                    'name': self.config.with_context(lang="en_US").name,
                    'city': self.config.company_id.city,
                    'ref_id': self.config.urbanpiper_store_identifier
                }
            ]
        }
        name_translations = self.config.get_field_translations('name')
        data['stores'][0]['translations'] = self._get_translations(name_translations, 'name')
        data = self.config.prepare_store_data(data)
        response_json = self._make_api_request(endpoint, data=data)
        return response_json

    def request_sync_menu(self):
        """
        Sync menu in urban piper.
        - Sync categories, products, attributes, values and taxes.
        """
        store_identifier = quote(self.config.urbanpiper_store_identifier, safe='')
        endpoint = f'external/api/v1/inventory/locations/{store_identifier}/'
        product_domain = [
            ('urbanpiper_pos_config_ids', 'in', self.config.ids),
            ('type', '!=', 'combo')
        ]
        # For the US & UK regions, there is an issue on the UrbanPiper side. They require the entire product catalog, but currently, we are only sending the updated products.
        full_sync_required_providers = ['justeat', 'grubhub', 'doordash', 'ubereats']
        products = self.config.env['product.template'].search(product_domain)
        pos_products = products
        flush = self.config.env.context.get('flush')
        if not flush and not any(provider.technical_name in full_sync_required_providers for provider in self.config.urbanpiper_delivery_provider_ids):
            pos_products = products.filtered(lambda product: (
                not product.urban_piper_status_ids or
                self.config.id not in product.urban_piper_status_ids.config_id.ids or
                any(ups.config_id.id in self.config.ids and not ups.is_product_linked for ups in product.urban_piper_status_ids)
            ))
        pos_products_without_pos_categ_ids = pos_products.filtered(lambda p: not p.pos_categ_ids)
        pos_other_categ_id = self.config.env['pos.category'].search([('name', 'ilike', 'other')], limit=1)
        if not pos_other_categ_id:
            pos_other_categ_id = self.config.env['pos.category'].create({
                'name': 'Other',
            })
        pos_products_without_pos_categ_ids.pos_categ_ids = pos_other_categ_id
        pos_categories = pos_products.pos_categ_ids
        # The UrbanPiper platform only supports a single level of sub-categories.
        pos_categories |= pos_categories.parent_id
        pos_attribute_products = pos_products.filtered(lambda p: p.attribute_line_ids)
        payload = {
            'flush_categories': flush,
            'categories': self._prepare_categories_data(pos_categories),                      # pos categories
            'flush_items': flush,
            'items': self._prepare_items_data(pos_products),                                  # pos products
            'flush_option_groups': flush,
            'option_groups': self._prepare_option_groups_data(pos_attribute_products),        # pos attributes
            'flush_options': flush,
            'options': self._prepare_option_data(pos_attribute_products),                     # pos attribute values
            'flush_taxes': flush,
            'taxes': self.config.prepare_taxes_data(pos_products),                            # pos taxes
            'flush_charges': flush,
            'charges': self._prepare_charges_data()                                           # pos charges
        }
        # If we have multiple products, we should increase the timeout to 90 seconds.
        response_json = self._make_api_request(endpoint, method='POST', data=payload, timeout=90)
        if response_json.get('status') == 'success':
            # logic for updating the status of the product in atlas based on config
            for product in pos_products:
                if (not product.urban_piper_status_ids or product.urban_piper_status_ids and
                        self.config.id not in product.urban_piper_status_ids.config_id.ids):
                    product.write({
                        'urban_piper_status_ids': [Command.create({
                            'product_tmpl_id': product.id,
                            'is_product_linked': True,
                            'config_id': self.config.id
                        })]
                    })
                elif product.urban_piper_status_ids and self.config.id in product.urban_piper_status_ids.config_id.ids:
                    product.urban_piper_status_ids.filtered(lambda p: p.config_id == self.config).write({
                        'is_product_linked': True
                    })
        if response_json.get('status') == 'success':
            self.config.urbanpiper_last_sync_date = datetime.now()
        return response_json

    def _get_translations(self, field_translations, field):
        translations = []
        for translation in field_translations[0]:
            lang = translation['lang'].split('_')[0]
            translations.append({
                'language': lang,
                field: translation['value']
            }) if lang in UP_LANGUAGES else None
        return translations

    def get_item_ref_id(self, product):
        return f'{product.id}-{self.db_uuid[0:5]}'

    def _prepare_categories_data(self, pos_categories):
        """
        Prepare categories data for urban piper.
        """
        category_lst = []
        for category in pos_categories:
            categ_dict = {
                'ref_id': str(category.id),
                'name': category.with_context(lang="en_US").name,
                'sort_order': category.sequence,
                'active': True,
                'img_url': self._get_public_image_url(category),
            }
            if category.parent_id:
                categ_dict['parent_ref_id'] = str(category.parent_id.id)
            name_translations = category.get_field_translations('name')
            categ_dict['translations'] = self._get_translations(name_translations, 'name')
            category_lst.append(categ_dict)
        return category_lst

    def _prepare_items_data(self, pos_products):
        """
        Prepare product data for urban piper.
        """
        item_lst = []
        for product in pos_products:
            product_price = product.list_price if not self.config.urbanpiper_pricelist_id \
                else self.config.urbanpiper_pricelist_id.sudo()._get_product_price(
                product, 1.0, uom=product.uom_id
            )
            item = {
                'ref_id': self.get_item_ref_id(product),
                'title': product.with_context(lang="en_US").name,
                'description': html2plaintext(product.with_context(lang="en_US").public_description) if product.public_description else '',
                'price': product.taxes_id.compute_all(
                    product_price, product.currency_id, 1)[self.config._get_total_tax_tag()],
                'weight': product.weight,
                'food_type': product.urbanpiper_meal_type,
                'category_ref_ids': [str(i) for i in product.pos_categ_ids.ids],
                'recommended': product.is_recommended_on_urbanpiper,
                'img_url': self._get_public_image_url(product),
                'available': True,
            }
            name_translations = product.get_field_translations('name')
            description_translations = product.get_field_translations('public_description')
            translations = []
            name_dict = {t['lang'].split('_')[0]: t['value'] for t in name_translations[0] if t['lang'].split('_')[0] in UP_LANGUAGES}
            desc_dict = {t['lang'].split('_')[0]: t['value'] for t in description_translations[0] if t['lang'].split('_')[0] in UP_LANGUAGES}
            for lang in UP_LANGUAGES:
                if lang in name_dict or lang in desc_dict:
                    translations.append({
                        'language': lang,
                        'title': name_dict.get(lang, ''),
                        'description': desc_dict.get(lang, '')
                    })
            item['translations'] = translations
            # dynamic tag syncing for provider tags and default tags
            tags = item.setdefault('tags', {})
            default_tags = []
            for product_tag in product.product_tag_ids:
                default_tags.append(product_tag.name)
            alcohol_tag = 'alcohol-present' if product.is_alcoholic_on_urbanpiper else 'alcohol-absent'
            if alcohol_tag not in default_tags:
                default_tags.append(alcohol_tag)
            tags['default'] = default_tags
            for provider in self.config.urbanpiper_delivery_provider_ids:
                tags[provider.technical_name] = default_tags
            updated_item = self.config.update_urbanpiper_item_data(item, product)
            item_lst.append(updated_item)
        return item_lst

    def _prepare_option_groups_data(self, pos_products):
        """
        Prepare option groups data for urban piper.
        - Attributes are option groups.
        """
        attribute_lst = []
        for product in pos_products:
            for attr_line in product.attribute_line_ids:
                group = {
                    'ref_id': f'{product.id}-{attr_line.attribute_id.id}',
                    'title': attr_line.attribute_id.with_context(lang="en_US").name,
                    'active': True,
                    'multi_options_enabled': bool(attr_line.attribute_id.display_type == 'multi'),
                    'item_ref_ids': [self.get_item_ref_id(product)],
                    'min_selectable': 0,
                    'max_selectable': 30 if any(provider.technical_name == "doordash" for provider in self.config.urbanpiper_delivery_provider_ids) else -1
                }
                if attr_line.attribute_id.display_type != 'multi':
                    group['min_selectable'] = 1
                    group['max_selectable'] = 1
                name_translations = attr_line.attribute_id.get_field_translations('name')
                group['translations'] = self._get_translations(name_translations, 'title')
                attribute_lst.append(group)
        return attribute_lst

    def _prepare_option_data(self, pos_products):
        """
        Prepare options data for urban piper.
        - Attribute values are options.
        """
        value_lst = []
        for product in pos_products:
            for option_group in product.attribute_line_ids:
                for option in option_group.value_ids:
                    product_option = self.config.env['product.template.attribute.value'].search([
                        ('ptav_active', '=', True),
                        ('product_tmpl_id', '=', product.id),
                        ('product_attribute_value_id', '=', option.id)
                    ], limit=1)
                    value_dict = {
                        'ref_id': f'{product.id}-{option.id}',
                        'title': option.with_context(lang="en_US").name,
                        'available': True,
                        'opt_grp_ref_ids': [f'{product.id}-{i}' for i in option.attribute_id.ids],
                        'price': product_option.price_extra or option.default_extra_price,
                        'food_type': product.urbanpiper_meal_type,
                    }
                    name_translations = option.get_field_translations('name')
                    value_dict['translations'] = self._get_translations(name_translations, 'title')
                    value_lst.append(value_dict)
        return value_lst

    def _prepare_charges_data(self):
        """
        Prepare charges data for urban piper.
        """
        product_packaging = self.config.env.ref('pos_urban_piper.product_packaging_charges', False)
        product_delivery = self.config.env.ref('pos_urban_piper.product_delivery_charges', False)

        def get_charge_data(product):
            return {
                'code': 'PC_F' if product == product_packaging else 'DC_F',
                'title': product.with_context(lang="en_US").name,
                'active': True,
               'structure': {
                    'applicable_on': 'order.order_subtotal',
                    'value': product.list_price
                },
                'item_ref_ids': ['all']
            }

        return [
            get_charge_data(product)
            for product in [product_packaging, product_delivery]
            if product and product.list_price > 0
        ]

    def register_item_toggle(self, products, status):
        """
        Enable/Disable product on urban piper store. (If menu is synced with urban piper)
        """
        product_lst_str = [self.get_item_ref_id(product) for product in products]
        endpoint = 'hub/api/v1/items/'
        payload = {
            'location_ref_id': self.config.urbanpiper_store_identifier,
            'item_ref_ids': product_lst_str,
            'option_ref_ids': [],
            'action': 'enable' if status else 'disable'
        }
        response_json = self._make_api_request(endpoint, method='POST', data=payload)
        return response_json

    def urbanpiper_attribute_value_toggle(self, values, status):
        """
        Enable/Disable the attribute's value on the urbanpiper store. (If menu is synced with urban piper)
        """
        value_lst_str = [f'{value.product_tmpl_id.id}-{value.product_attribute_value_id.id}' for value in values]
        endpoint = 'hub/api/v1/items/'
        payload = {
            'location_ref_id': self.config.urbanpiper_store_identifier,
            'item_ref_ids': [],
            'option_ref_ids': value_lst_str,
            'action': 'enable' if status else 'disable'
        }
        response_json = self._make_api_request(endpoint, method='POST', data=payload)
        return response_json

    def request_status_update(self, order_id, new_status, code=None):
        """
        Update status in Urban Piper
        """
        endpoint = f'external/api/v1/orders/{order_id}/status/'
        payload = {
            'new_status': new_status,
            'reason_code': code
        }
        response_json = self._make_api_request(endpoint, method='PUT', data=payload)
        if response_json:
            if response_json.get('status') == 'success':
                return True, ''
            else:
                return False, response_json.get('message') or next(iter(response_json.get("errors", {}).values()), "")
        else:
            return False, 'Failed to update status in Urban Piper'

    def urbanpiper_order_reference_update(self, order):
        """
        Update order reference in Urban Piper
        """
        endpoint = f'external/api/v1/orders/{order.delivery_identifier}/'
        payload = {
            "reference_id": order.name
        }
        self._make_api_request(endpoint, method='PUT', data=payload)

    def urbanpiper_store_status_update(self, status):
        """
        Change store status in urban piper.
        """
        provider_name = self.config._context.get('provider_name')
        platforms = [provider_name] if provider_name else [p.technical_name for p in self.config.urbanpiper_delivery_provider_ids]
        if platforms:
            payload = {
                'location_ref_id': self.config.urbanpiper_store_identifier,
                'platforms': platforms,
                'action': 'enable' if status else 'disable',
            }
            self._make_api_request('hub/api/v1/location/', data=payload)

    def _get_jpeg_datas(self, datas):
        """
        Get the image data in jpeg format.
        """
        try:
            data_uri = self.config.env['ir.qweb'].with_context(webp_as_jpg=True)._get_converted_image_data_uri(datas)
            _header, base64_data = data_uri.split('base64,', 1)
            return base64_data
        except TypeError:
            return datas

    def _get_public_image_url(self, record):
        """
        Get public image URL for the given record (product or category).
        Converts webp to jpeg if necessary.
        """
        base_url = self.config.urbanpiper_webhook_url
        image_data = record.image_1920 if record._name == 'product.template' else record.image_128
        attachment = record.env['ir.attachment'].search([
            ('res_model', '=', record._name),
            ('res_id', '=', record.id),
            ('type', '=', 'binary'),
            ('public', '=', True),
            ('mimetype', '=', 'image/jpg'),
        ], limit=1)
        datas = self._get_jpeg_datas(image_data)
        if attachment:
            attachment.datas = datas
        else:
            attachment = record.env['ir.attachment'].create({
                'name': record.name,
                'type': 'binary',
                'datas': datas,
                'res_model': record._name,
                'res_id': record.id,
                'public': True,
                'mimetype': 'image/jpg',
            })
        local_url = attachment.local_url
        return url_join(base_url, local_url)

    def request_refresh_webhooks(self):
        """
        If customer uses multi db on the same URL. UrbanPiper only stores one webhook per URL.
        When the user switches the database, they can press the refresh webhook button to
        update the webhook parameters according to the new database.
        """
        self.config.urbanpiper_webhook_url = self.config.get_base_url()   # registring webhook
        self._register_webhook()
        wehbook_json = self._make_api_request('external/api/v1/webhooks?limit=50', method='GET')
        webhooks = wehbook_json.get('webhooks')
        response_json = {}
        if webhooks:
            for webhook in webhooks:
                if self.config.urbanpiper_webhook_url and self.config.urbanpiper_webhook_url in webhook.get('url'):
                    payload = {
                        'active': True,
                        'event_type': webhook.get('event_type'),
                        'retrial_interval_units': 'seconds',
                        'url': webhook.get('url'),
                        'headers': {
                            'X-Urbanpiper-Uuid': self.config.env['ir.config_parameter'].sudo().get_param('pos_urban_piper.uuid')
                        }
                    }
                    wehbook_id = webhook.get('webhook_id')
                    response_json = self._make_api_request(f'external/api/v1/webhooks/{wehbook_id}/', data=payload, method='PUT')
        return response_json

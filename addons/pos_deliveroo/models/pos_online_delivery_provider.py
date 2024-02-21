# coding: utf-8

import requests
import time
import json
import base64
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError, UserError
from datetime import datetime
from odoo.tools.image import image_data_uri

class PosOnlineDeliveryProvider(models.Model):
    _inherit = 'pos.online.delivery.provider'

    webhook_secret = fields.Char('Webhook Secret', copy=False)
    site_id = fields.Integer('Site Location ID', copy=False)
    code = fields.Selection(selection_add=[('deliveroo', "Deliveroo")], ondelete={'deliveroo': 'set default'})
    busy_time = fields.Integer('Busy Time')
    quiet_time = fields.Integer('Quiet Time')
    mealtime_ids = fields.One2many('pos.online.delivery.mealtime', 'provider_id', string='Meal Times')
    brand_id = fields.Char('Brand ID', copy=False)
    site_description = fields.Text('Deliveroo Description', copy=False, size=500)

    def write(self, vals):
        if vals.get('busy_time') or vals.get('quiet_time'):
            response = self._set_site_workload_time(vals.get('quiet_time', self.quiet_time), vals.get('busy_time', self.busy_time))
            if response:
                self.quiet_time = response.get('quiet')
                self.busy_time = response.get('busy')
        return super().write(vals)

    @api.onchange('state')
    def _onchange_state(self):
        super()._onchange_state()
        if self.code == 'deliveroo' and self.state in ('enabled', 'test'):
            if not self.webhook_secret:
                raise ValidationError(_('Please fill in the webhook secret provided by Deliveroo.'))
            if not self.site_id:
                raise ValidationError(_('Please fill in the site location ID provided by Deliveroo.'))
            
    def ensure_enabled(self):
        if self.code == "deliveroo" and self.state == "disabled":
            return False
        return super().ensure_enabled()

    def _get_delivery_acceptation_time(self):
        res = super()._get_delivery_acceptation_time()
        if self.code == "deliveroo":
            if self.env.company.country_code in ['KW', 'AE']:
                return 7
            return 10
        return res
    
    def _get_api_url(self, suffix: str):
        self.ensure_enabled()
        if self.code == "deliveroo":
            if self.state == "enabled":
                return "https://api.developers.deliveroo.com" + suffix
            if self.state == "test":
                return "https://api-sandbox.developers.deliveroo.com" + suffix
        return super()._get_api_url()
            
    #ORDERS API

    def _accept_order(self, id: int, status: str = ""):
        """
        used for tablet-less flow
        """
        self.ensure_enabled()
        if not status:
            status = "accepted"
        response = requests.patch(
            self._get_api_url(f"/order/v1/orders/{id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={"status": status},
        )
        return response.status_code == 204

    def _reject_order(self, id: int, rejected_reason: str = "busy"):
        """
        used for tablet-less flow
        the rejected reason can be ["busy", "closing_early", "ingredient_unavailable", "other"]
        """
        self.ensure_enabled()
        response = requests.patch(
            self._get_api_url(f"/order/v1/orders/{id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={
                "status": "rejected",
                "reject_reason": rejected_reason,
            },
        )
        return response.status_code == 204

    def _confirm_accepted_order(self, id: int):
        """
        used for tablet-less flow
        """
        self.ensure_enabled()
        response = requests.patch(
            self._get_api_url(f"/order/v1/orders/{id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={
                "status": "confirmed",
            },
        )
        return response.status_code == 204

    def _send_preparation_status(self, id: int, stage: str, delay: int = 0):
        self.ensure_enabled()
        if stage in ['in_kitchen', 'ready_for_collection_soon', 'ready_for_collection', 'collected']:
            json = {
                'stage': stage,
                'occurred_at': str(datetime.utcnow().replace(microsecond=0).isoformat()) + 'Z'
            }
            if stage == 'in_kitchen'and delay in [0, 2, 4, 6, 10]:
                json['delay'] = delay
            response = requests.post(
                self._get_api_url(f"/order/v1/orders/{id}/prep_stage"),
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                    "Authorization": f"Bearer {self._get_access_token()}",
                },
                json=json,
            )
            return response.status_code == 200
        return False
    
    #AUTHENTIFICATION API

    def _refresh_access_token(self) -> str:
        self.ensure_one()
        self.ensure_enabled()
        if self.code != "deliveroo":
            return super()._refresh_access_token()
        if self.state == "enabled":
            AUTH_HOST = 'https://auth.developers.deliveroo.com/oauth2/token'
        elif self.state == "test":
            AUTH_HOST = 'https://auth-sandbox.developers.deliveroo.com/oauth2/token'

        # Encode client_id:client_secret in base64
        auth_string = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        # Data for the request
        data = {
            'grant_type': 'client_credentials'
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {auth_string}'
        }

        # Make the POST request
        response = requests.post(AUTH_HOST, headers=headers, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data.get("access_token")
            self.access_token_expiration_timestamp = time.time() + token_data.get(
                "expires_in"
            )
            return token_data.get("access_token")
        return False
    
    #MENU API

    def action_upload_menu(self):
        self.ensure_enabled()
        if self.code == "deliveroo":
            self._upload_menu(f'Deliveroo menu {self.brand_id}', self._get_menu_json())
        
    def _get_menu_json(self):
        #see https://api-docs.deliveroo.com/v2.0/reference/put_v1-brands-brand-id-menus-id
        
        menu = {
            'categories': [],
            'mealtimes': [],
            'items': [],
            'modifiers': [],
        }
        all_categories = self.pos_category_ids if self.pos_category_ids else self.available_pos_category_ids
        all_products = self.env['product.product'].search([('pos_categ_ids', 'in', all_categories.ids), ('available_in_pos', '=', True)])
        decimal_places = self.payment_method_id.journal_id.currency_id.decimal_places if self.payment_method_id.journal_id.currency_id else self.env.company.currency_id.decimal_places
        language_code = self._language_code_to_deliveroo_language_code(self.env.lang)
        all_modifiers = all_products.attribute_line_ids.attribute_id.filtered(lambda a: a.create_variant == 'no_variant')
        all_modifier_values = all_products.attribute_line_ids.value_ids.filtered(lambda a: a.attribute_id.create_variant == 'no_variant')
        all_combos = all_products.combo_ids

        #check all resources format validity
        #see https://api-docs.deliveroo.com/v2.0/docs/menu-api-guidelines
        errors = []
        for category in all_categories:
            if len(category.name) < 3:
                errors.append(_("The category %s has a name too short for Deliveroo. Please extend it (should be between 3 and 120 characters).", category.name))
            elif len(category.name) > 120:
                errors.append(_("The category %s has a name too long for Deliveroo. Please shorten it (should be between 3 and 120 characters).", category.name))
        
        for product in all_products:
            if len(product.name) < 2:
                errors.append(_("The product %s has a name too short for Deliveroo. Please extend it (should be between 2 and 120 characters).", product.name))
            elif len(product.name) > 120:
                errors.append(_("The product %s has a name too long for Deliveroo. Please shorten it (should be between 2 and 120 characters).", product.name))

        for modifier_value in all_modifier_values:
            if len(modifier_value.name) < 2:
                errors.append(_("The modifier value %s has a name too short for Deliveroo. Please extend it (should be between 2 and 120 characters).", modifier_value.name))
            elif len(modifier_value.name) > 120:
                errors.append(_("The modifier value %s has a name too long for Deliveroo. Please shorten it (should be between 2 and 120 characters).", modifier_value.name))

        if len(errors):
            raise UserError('\n'.join(errors))

        #fill category
        for category in all_categories:
            cat = {
                'id': f'category{category.id}',
                'name': {
                    language_code: category.name,
                },
                'item_ids': [f'product{item.id}' for item in all_products if any(categ == category.id for categ in item.pos_categ_ids.ids)],
            }
            menu['categories'].append(cat)

        #fill items
            for item in all_products:
                if not item.combo_ids and not self._is_item_valid_tax_rate(item):
                    raise UserError(_("The tax rate of the product %s is not valid for Deliveroo. Please check the tax configuration of the product.", item.name))
                deliveroo_item = {
                    'id': f'product{item.id}',
                    'name': {
                        language_code: item.name,
                    },
                    # 'description': {
                    #     language_code: item.description_sale,
                    # }, TODO maybe we should think about adding a description field to product in this food delivery or even in the point_of_sale module ?
                    'price_info': {
                        'price': int(item.lst_price * (10**decimal_places)),
                        # 'overrides': [{}], TODO maybe use this for combo ?
                        # 'fees': [{}], TODO if we wanna add fees ?
                    },
                    'plu': str(item.id),
                    'image': {
                        'url': image_data_uri(item.image_1920), #TODO see if this returns an URL
                    },
                    'tax_rate': str(item.taxes_id.amount) if not item.combo_ids else '0.0',
                    'contains_alcohol': False, #TODO see if we can get this information from the product or I'll have to add a checkbox on the product form
                    'type': 'ITEM', #TODO should use type item for product, type choice for modifiers. I still do not know about combos
                    'allergies': [],
                    'classifications': [],
                    'diets': [],
                }
                if item.combo_ids:
                    deliveroo_item['modifier_ids'] = [f'combo{id}' for id in item.combo_ids.ids]
                elif item.attribute_line_ids.attribute_id.filtered(lambda a: a.create_variant == 'no_variant'):
                    deliveroo_item['modifier_ids'] = [f'attribute{modifier_value.id}' for modifier_value in item.attribute_line_ids.attribute_id.filtered(lambda a: a.create_variant == 'no_variant')]
                
                menu['items'].append(deliveroo_item)
            
            for modifier_value in all_modifier_values:
                deliveroo_item = {
                    'id': f'attribute_value{modifier_value}',
                    'name': {
                        language_code: modifier_value.name,
                    },
                    'price_info': {
                        'price': int(modifier_value.default_extra_price * (10**decimal_places)),
                    },
                    'plu': str(modifier_value.id),
                    'tax_rate': '0.0',
                    'contains_alcohol': False,
                    'type': 'CHOICE',
                }
                menu['items'].append(deliveroo_item)


        #fill mealtimes TODO see if we can only send a mealtime array that is empty (meaning all day/every day)
        #else, the schedule should have all hours of the day.
        #Another option is to link categories to mealtime, with this, we would send the default menu with all categories
        #and no mealtime and send a menu with the desired categories for each other mealtime
            for mealtime_id in self.mealtime_ids:
                mt = {
                    'id': f'mealtime{mealtime_id.id}',
                    'name': {
                        language_code: mealtime_id.name if mealtime_id.name else str(mealtime_id.id),
                    },
                    'image': {
                        'url': image_data_uri(mealtime_id.image_1920),
                    },
                    'category_ids': [str(category.id) for category in all_categories],
                    'schedule': [
                        {
                            'day_of_week': int(mealtime_id.weekday),
                            'time_periods': [
                                {
                                    'start': self._float_to_time(mealtime_id.start_hour),
                                    'end': self._float_to_time(mealtime_id.end_hour),
                                }
                            ]
                        }
                    ],
                }
                if mealtime_id.description or self.site_description:
                    mt['description'] = {
                        language_code: mealtime_id.description or self.site_description,
                    }
                menu['mealtimes'].append(mt)

        #fill modifiers (this handles product variants with create_variant = 'no_variant')
            for modifier in all_modifiers:
                mod = {
                    'id': f'attribute{modifier.id}',
                    'name': {
                        language_code: modifier.name,
                    },
                    'item_ids': [f'attribute_value{modifier_value.id}' for modifier_value in all_modifier_values],
                    # 'min_selection': 0,
                    # 'max_selection': 1, TODO see if we want to add this ?
                    # 'repeatable': True, TODO not sure what it means
                }
                menu['modifiers'].append(mod)

            for combo in all_combos:
                mod = {
                    'id': f'combo{combo.id}',
                    'name': {
                        language_code: combo.name,
                    },
                    'item_ids': [f'product{item.id}' for item in combo.combo_line_ids.product_id],
                }
                menu['modifiers'].append(mod)
        return menu

    @api.model
    def _float_to_time(self, hours_float):
        hours, minutes = divmod(int(hours_float * 60), 60)
        return f'{hours:02d}:{minutes:02d}'

    @api.model
    def _language_code_to_deliveroo_language_code(self, language_code):
        available_code_per_country = {
            'AE': ['en', 'ar'],
            'BE': ['fr', 'nl', 'en'],
            'FR': ['fr', 'en'],
            'HK': ['zh', 'en'],
            'IE': ['en'],
            'IT': ['it', 'en'],
            'KW': ['ar', 'en'],
            'SG': ['zh', 'en'],
            'GB': ['en'],
            'QA': ['ar', 'en'],
            'US': ['en'], #TODO remove this as this is only to test
        }

        small_lc = language_code.split('_')[0]
        if small_lc not in available_code_per_country.get(self.env.company.country_code, []):
            return 'en'
        return small_lc

    def _is_item_valid_tax_rate(self, item):
        available_tax_rate_per_country = {
            'AE': [0.0, 5.0],
            'BE': [0.0, 6.0, 12.0, 21.0],
            'FR': [0.0, 2.1, 5.5, 10.0, 20.0],
            'HK': [0.0],
            'IE': [0.0, 9.0, 13.5, 23.0],
            'IT': [0.0, 4.0, 5.0, 10.0, 22.0],
            'KW': [0.0],
            'SG': [0.0, 9.0],
            'GB': [0.0, 5.0, 12.5, 20.0],
            'QA': [0.0],
            'US': [21.0] #TODO remove this as this is only to test
        }
        if item.taxes_id.amount not in available_tax_rate_per_country.get(self.env.company.country_code, []):
            return False
        return True
            

    def _upload_menu(self, name, menu):
        self.ensure_enabled()
        if self.code == 'deliveroo':
            response = requests.put(
                self._get_api_url(f"/menu/v1/brands/{self._get_brand_id()}/menus/{self.site_id}"),
                headers={
                    "accept": "application/json",
                    'content-type': 'application/json',
                    "Authorization": f"Bearer {self._get_access_token()}",
                },
                json={
                    'name': name,
                    'menu': menu,
                    'site_ids': [str(self.site_id)],
                }
            )
            if response.status_code == 200:
                self.last_menu_synchronization = fields.Datetime.now()
                return True
            return False
        else:
            return super()._upload_menu()

    #SITE API
    def _get_brand_id(self):
        self.ensure_enabled()
        if self.brand_id:
            return self.brand_id
        response = requests.get(
            self._get_api_url(f"/site/v1/restaurant_locations/{self.site_id}"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        if response.status_code == 200:
            brand_id_array = response.json().get("brand_id")
            self.brand_id = brand_id_array[0]
            return self.brand_id
        return False
    
    def _get_site_status(self):
        self.ensure_enabled()
        response = requests.get(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/status"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json().get('status') if response.status_code == 200 else False

    def _change_site_status_mode(self, status):
        #send to deliveroo the information about the restaurant status [open, closed, ready_to_open]
        self.ensure_enabled()
        if status not in ['OPEN', 'CLOSED', 'READY_TO_OPEN']:
            return False
        if self._get_site_status(self) == status:
            return True
        response = requests.put(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/status"),
            headers={
                "accept": "application/json",
                'content-type': 'application/json',
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json = {
                'status': status,
            },
        )
        return response.status_code == 200
    
    def _get_site_workload_mode(self):
        self.ensure_enabled()
        response = requests.get(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/workload/mode"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json().get('mode') if response.status_code == 200 else False
    
    def _set_site_workload_mode(self, mode):
        self.ensure_enabled()
        if mode not in ['BUSY', 'QUIET']:
            return False
        if self._get_site_workload_mode() == mode:
            return True
        response = requests.put(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/workload/mode"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json().get('mode') if response.status_code == 200 else False
    
    def _set_site_workload_time(self, quiet_time, busy_time):
        self.ensure_enabled()
        response = requests.put(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/workload/times"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json = {
                'quite': quiet_time,
                'busy': busy_time,
            },
        )
        return response.json() if response.status_code == 200 else False

    def _get_site_brand_id(self):
        self.ensure_enabled()
        response = requests.get(
            self._get_api_url(f"/site/v1/restaurant_locations/{self.site_id}"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return json.loads(response.content) if response.status_code == 200 else False
    
    def _get_site_opening_hours(self):
        self.ensure_enabled()
        response = requests.get(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/opening_hours"),
            headers={
                "accept": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
        )
        return response.json() if response.status_code == 200 else False
    
    def _update_site_opening_hours(self, opening_hours):
        self.ensure_enabled()
        response = requests.post(
            self._get_api_url(f"/site/v1/brands/{self._get_brand_id()}/sites/{self.site_id}/opening_hours"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {self._get_access_token()}",
            },
            json={
                'opening_hours': opening_hours,
            }
        )
        return response.json() if response.status_code == 200 else False

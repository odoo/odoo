from odoo.http import request
import json
import requests
from odoo import http, tools
from odoo.exceptions import UserError
import logging
from ..utils import image_utils  # To access get_image_as_base64

_logger = logging.getLogger(__name__)


class MenuSyncController(http.Controller):
    @http.route('/sync_menus', type='json', auth='public', methods=['POST'])
    def sync_menus(self):
        """
            Endpoint to synchronize all menus from an external API.
            This is for restaurants having <80 menus
        """
        try:
            config_params = self._validate_config()
            _logger.info('\033[94m======================== GETTING RESTAURANT MENUS ========================\033[0m')  # Blue
            menus = self._fetch_menus(config_params['restaurant_id'], config_params['synchronize_menus_url'], config_params['odoo_secret_key'])
            self._process_menus(menus, config_params['base_s3_url'])

            _logger.info('\033[94m======================== FINISH GETTING RESTAURANT MENUS ========================\033[0m')  # Blue
            return {'status': 'success', 'message': 'Menus synchronized successfully'}

        except Exception as e:
            print(f"Error while synchronizing menus: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    @http.route('/sync_menus_by_range', type='json', auth='public', methods=['POST'])
    def sync_menus_by_range(self):
        """
            Endpoint to synchronize menus by range from an external API.
            This is for restaurants having >80 menus
        """
        try:
            config_params = self._validate_config()
            _logger.info(
                '\033[94m======================== GETTING RESTAURANT MENUS ========================\033[0m')  # Blue

            menus = self._fetch_menus_by_range(config_params['restaurant_id'], config_params['synchronize_menus_url'], config_params['odoo_secret_key'])
            self._process_menus(menus, config_params['base_s3_url'])

            _logger.info(
                '\033[94m======================== FINISH GETTING RESTAURANT MENUS ========================\033[0m')  # Blue
            return {'status': 'success', 'message': 'Menus synchronized successfully'}

        except Exception as e:
            print(f"Error while synchronizing menus: {str(e)}")
            return {'status': 'error', 'message': str(e)}

    # Helper methods

    @staticmethod
    def _validate_config():
        """Validate required configuration parameters."""
        config_params = {
            'synchronize_menus_url': tools.config.get('synchronize_menus_url'),
            'base_s3_url': tools.config.get('base_s3_url'),
            'secret_key': tools.config.get('secret_key'),
            'restaurant_id': request.env['ir.config_parameter'].sudo().get_param('restaurant_id'),
            'odoo_secret_key': tools.config.get('odoo_secret_key')
        }

        for key, value in config_params.items():
            if not value:
                _logger.error(f"{key} is not valid in Config")
                raise UserError(f"There is no {key} in Config")
        _logger.info('\033[92mConfiguration keys are validated\033[0m')  # Green
        return config_params

    @staticmethod
    def _fetch_menus(restaurant_id, synchronize_menus_url, odoo_secret_key):
        """Fetch menus from the external API."""
        response = requests.get(f"{synchronize_menus_url}{restaurant_id}", headers={'x-odoo-key': odoo_secret_key})
        if response.status_code != 200:
            error_msg = {'error': 'Failed to fetch menus from the external API'}
            result = dict(
                success=False,
                message=http.Response(json.dumps(error_msg), content_type='application/json'),
            )
            _logger.error('Error while fetching menus from Menupro Server: ', json.dumps(result))
            return json.dumps(result)

        return response.json()

    @staticmethod
    def _fetch_menus_by_range(restaurant_id, synchronize_menus_url, odoo_secret_key):
        """Fetch menus from the external API."""
        data = json.loads(request.httprequest.data)
        skip = data['skip']
        limit = data['limit']
        response = requests.get(synchronize_menus_url + restaurant_id + '/' + str(limit) + '/' + str(skip), headers={'x-odoo-key': odoo_secret_key})

        if response.status_code != 200:
            error_msg = {'error': 'Failed to fetch menus from the external API'}
            result = dict(
                success=False,
                message=http.Response(json.dumps(error_msg), content_type='application/json'),
            )
            return json.dumps(result)

        return response.json()

    def _process_menus(self, menus, s3_base_url):
        """Process the fetched menus."""
        pos_menus_model = http.request.env['product.template'].sudo()
        product_category_model = http.request.env['product.category'].sudo()
        pos_category_model = http.request.env['pos.category'].sudo()
        account_tax = http.request.env['account.tax'].sudo().search([('amount', '=', 0.000)])

        created_menus = menus['created']
        updated_menus = menus['updated']
        deleted_menus = menus['deleted']

        for menu_data in created_menus:
            self._create_menu(menu_data, pos_menus_model, product_category_model, pos_category_model, account_tax, s3_base_url)

        for menu_data in updated_menus:
            self._update_menu(menu_data, pos_menus_model, product_category_model, pos_category_model, account_tax, s3_base_url)

        for menu_id in deleted_menus:
            self._deactivate_menu(menu_id, pos_menus_model)

    def _create_menu(self, menu_data, pos_menus_model, product_category_model, pos_category_model, account_tax, s3_base_url):
        """Create a new menu."""
        existing_menu = pos_menus_model.search([('menupro_id', '=', menu_data['_id'])], limit=1)
        if existing_menu:
            # If the menu exists already then update it
            self._update_menu(menu_data, pos_menus_model, product_category_model, pos_category_model, account_tax, s3_base_url)
        else:
            menu_obj = self._prepare_menu_obj(menu_data, s3_base_url)
            menu_obj.update({
                'menupro_id': menu_data['_id'],
                'available_in_pos': True,
                'taxes_id': [(6, 0, account_tax.ids)],
            })
            if 'menuCateg' in menu_data and menu_data['menuCateg']:
                self._update_menu_category(menu_obj, menu_data, product_category_model, pos_category_model, s3_base_url)

            created_menu = pos_menus_model.create_only_in_odoo(menu_obj)

            # Update the category in which the menu will be filtered in POS interface
            self._update_pos_categories(created_menu, menu_data, pos_category_model)

    def _update_menu(self, menu_data, pos_menus_model, product_category_model, pos_category_model, account_tax, s3_base_url):
        """Update an existing menu."""
        menu = pos_menus_model.search([('menupro_id', '=', menu_data['_id'])], limit=1)
        if menu:
            menu_obj = self._prepare_menu_obj(menu_data, s3_base_url)
            menu.write_only_in_odoo(menu_obj)

            if 'menuCateg' in menu_data and menu_data['menuCateg']:
                self._update_menu_category(menu_obj, menu_data, product_category_model, pos_category_model, s3_base_url)
                menu.write_only_in_odoo(menu_obj)
        else:
            self._create_menu(menu_data, pos_menus_model, product_category_model, pos_category_model, account_tax, s3_base_url)

    @staticmethod
    def _deactivate_menu(menu_id, pos_menus_model):
        """Deactivate a deleted menu."""
        menu = pos_menus_model.search([('menupro_id', '=', menu_id)])
        if menu:
            menu.write_only_in_odoo({'available_in_pos': False})

    @staticmethod
    def _prepare_menu_obj(menu_data, s3_base_url):
        """Prepare a menu object for creation or update."""
        picture = image_utils.get_image_as_base64(s3_base_url + menu_data['picture']) if 'picture' in menu_data and menu_data[
            'picture'] else None
        picture_url = s3_base_url + menu_data['picture'] if 'picture' in menu_data and menu_data['picture'] else None

        return {
            'name': menu_data['title'],
            'list_price': menu_data['price'],
            'picture': picture_url,
            'image_1920': picture
        }

    @staticmethod
    def _update_menu_category(menu_obj, menu_data, product_category_model, pos_category_model, s3_base_url):
        """Update or create a menu category."""
        category_data = menu_data['menuCateg']
        product_category = product_category_model.search([('menupro_id', '=', category_data['_id'])])
        pos_category = pos_category_model.search([('menupro_id', '=', category_data['_id'])])

        category_picture = image_utils.get_image_as_base64(
            s3_base_url + category_data['picture']) if 'picture' in category_data and category_data[
            'picture'] else None
        category_picture_url = s3_base_url + category_data[
            'picture'] if 'picture' in category_data and category_data['picture'] else None

        # This is the category of product
        if not product_category:
            category_obj = {
                'menupro_id': category_data['_id'],
                'name': category_data['menuProName'],
                'type_name': category_data['typeName'],
                'picture': category_picture_url,
            }
            product_category = product_category_model.create(category_obj)

        # This is the category in which the product will be FILTERED in POS
        if not pos_category:
            category_obj = {
                'menupro_id': category_data['_id'],
                'name': category_data['menuProName'],
                'type_name': category_data['typeName'],
                'picture': category_picture_url,
                'image_128': category_picture,
                'option_name': category_data['_id']
            }
            pos_category = pos_category_model.create(category_obj)

        menu_obj['categ_id'] = product_category.id

        # Overwrite the pos_category (only 1 category)
        menu_obj['pos_categ_ids'] = [(5, 0, 0)]  # This will remove all existing relations
        menu_obj['pos_categ_ids'].append((4, pos_category.id))  # Add the new category

    @staticmethod
    def _update_pos_categories(menu, menu_data, pos_category_model):
        """Update POS categories for a menu."""
        if 'menuCateg' in menu_data and menu_data['menuCateg']:
            pos_category = pos_category_model.search([('menupro_id', '=', menu_data['menuCateg']['_id'])])
            if pos_category:
                menu.write({
                    'pos_categ_ids': [(4, id) for id in pos_category.ids + menu.pos_categ_ids.ids],
                })

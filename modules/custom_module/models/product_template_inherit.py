from odoo import models, fields, api, tools, http
import requests
from datetime import datetime
import logging
from odoo.http import request
import json
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _description = 'Products table'

    menupro_id = fields.Char(string='MenuPro ID')
    picture = fields.Char(string='Picture')
    pos_preferred_location_id = fields.Many2one(
        'stock.location',
        string="Emplacement préféré pour le POS",
        domain=[('usage', '=', 'internal')],
        help="Lors des ventes en POS, le stock sera prioritairement prélevé de cet emplacement, même si la quantité disponible est insuffisante."
    )
    margin = fields.Float(string="Marge (%)", compute="_compute_margin", store=True)
    kitchen_notes = fields.Text (string="Notes de cuisine")

    def sync_menus(self):
        """ To be triggered to synchronize menus in Odoo Menupro Restaurant and Menupro mobile """
        url = tools.config.get("synchronize_menus_endpoint")
        base_url = request.httprequest.host_url
        data = {
            'created': [],
            'updated': [],
            'deleted': []
        }
        headers = {'Content-Type': 'application/json'}
        response = requests.post(base_url + url, headers=headers, data=json.dumps(data), timeout=1200)
        return response

    def create_only_in_odoo(self, vals):
        """ This is a dedicated method to CREATE product (A.K.A. menu) ONLY in Odoo and not in MenuPro Server"""
        return super(ProductTemplate, self).create(vals)

    def write_only_in_odoo(self, vals):
        """ This is a dedicated method to UPDATE product (A.K.A. menu) ONLY in Odoo and not in MenuPro Server"""
        return super(ProductTemplate, self).write(vals)

    def create(self, vals):
        if isinstance(vals, list):
            # Filter the consu product and non consu ones
            consu_products = [val for val in vals if val.get('type') == 'consu']
            non_consu_products = [val for val in vals if val.get('type') != 'consu']

            # Create only in Odoo
            if non_consu_products:
                return self.create_only_in_odoo(non_consu_products)

            # Create in MP server and Odoo
            for product in vals:
                self._process_single_product(product)
            return super(ProductTemplate, self).create(consu_products)

        if 'type' in vals and vals['type'] != 'consu':
            # Create it only in Odoo app
            return self.create_only_in_odoo(vals)

        # Create the rest in MP server and Odoo
        self._process_single_product(vals)
        return super(ProductTemplate, self).create(vals)

    def _process_single_product(self, vals):
        """Helper method to process a single product creation."""
        api_url = tools.config.get("menu_url")
        odoo_secret_key = tools.config.get("odoo_secret_key")
        if not odoo_secret_key:
            _logger.error("odoo_secret_key missing ")

        # Create the menu in MenuPro Server
        data = self.prepare_data(vals)
        response = requests.post(api_url, json=data, headers={'x-odoo-key': odoo_secret_key})
        status_code = response.status_code
        response_data = response.json()

        # Save the associated menupro ID
        menupro_id = response.json().get('id')
        vals['menupro_id'] = menupro_id

        # Upload image if present
        if 'image_1920' in vals and vals["image_1920"]:
            self._upload_image_to_menupro(vals, menupro_id)
        _logger.info('\033[92mSuccessfully created menu in MenuPro\033[0m')
        return {"status_code": status_code, "response_data": response_data}

    def write(self, vals):
        res = super(ProductTemplate, self).write(vals)
        for product in self:
            if product.type != 'consu':
                continue
            self._create_or_update_menupro_menu(product)

        # If image_1920 is updated, upload the new image to S3 and update MenuPro
        if 'image_1920' in vals and vals["image_1920"]:
            for product in self:
                if product.menupro_id:
                    self._upload_image_to_menupro(vals, product.menupro_id)
        _logger.info(f'\033[92mSuccessfully updated the menu with vals {vals} in MenuPro and Odoo Servers\033[0m')  # Green
        return res

    def _create_or_update_menupro_menu(self, product):
        # Get data
        data = self.prepare_data(product)
        odoo_secret_key = tools.config.get("odoo_secret_key")

        # If product is found in product.template => update (in case of creation an etiquette)
        if product.id:
            # If the menupro_id is undefined or null -> pass
            if product.menupro_id is None or product.menupro_id is False:
                return

            # Update the existing MenuPro menu
            api_url = f"{tools.config.get('menu_url')}/{product.menupro_id}"
            existing_product = self.env['product.template'].search([('id', '=', product.id)], limit=1)

            # Update category
            if 'categ_id' in product:
                category = http.request.env['product.category'].sudo().search(
                    [('id', '=', product['categ_id'].id)]).menupro_id
                if category is not None:
                    # Update in the menupro Server
                    data['menuCateg'] = category

            # Call API to update menu in MenuPro
            response = requests.patch(api_url, json=data,  headers={'x-odoo-key': odoo_secret_key})
            if response.status_code != 200:
                return "There is a problem while updating Menupro Menu"

        # If product not found => create
        else:
            # Create a new MenuPro menu
            product = super(ProductTemplate, self).create(product)
            api_url = tools.config.get("create_menu_url")
            data = self.prepare_data(product)
            response = requests.post(api_url, json=data, headers={'x-odoo-key': odoo_secret_key})
            if response.status_code == 200:
                menupro_id = response.json().get('id')
                product.write({'menupro_id': menupro_id})

    def _upload_image_to_menupro(self, vals, menupro_id):
        try:
            # Decode the image and extract the type
            image_data = self.decode_image(vals['image_1920'])
            image_type = image_data[1]
            image_decoded = image_data[0]

            # Get signed url
            response_image = self.get_s3_signed_url(f'menu_image.{image_type}', menupro_id)

            # Get from conf
            store_picture_url = tools.config.get('store_picture_url')
            odoo_secret_key = tools.config.get("odoo_secret_key")

            # Upload to S3
            self.upload_image_to_s3(image_decoded, image_type, response_image['signedurl'], odoo_secret_key )

            # Store picture key

            data = {'menu_id': menupro_id, 'picture': response_image['key']}
            response_store = requests.post(store_picture_url, json=data,  headers={'x-odoo-key': odoo_secret_key})
            response_store.raise_for_status()
            _logger.info(f"\033[94mPicture uploaded successfully {response_image['key']}\033[0m")  # Green

            base_s3_url = tools.config.get('base_s3_url')
            if base_s3_url:
                vals['picture'] = f"{base_s3_url}/{response_image['key']}"
            else:
                _logger.error('There is no base_s3_url in Config')
                raise UserError("There is no base_s3_url in Config")
        except Exception as e:
            _logger.error(f"Error processing image: {e}")
            raise UserError(f"Error processing image: {e}")

    def unlink(self):
        """ Delete menu from MenuPro server AND Odoo database """
        api_url = tools.config.get("delete_menu_url")
        odoo_secret_key = tools.config.get("odoo_secret_key")

        for product in self:
            if product.menupro_id:
                menupro_id = product.menupro_id
                url = f"{api_url}/{menupro_id}"
                requests.delete(url, headers={'x-odoo-key': odoo_secret_key})

        # Call the parent unlink method to delete the product in Odoo
        _logger.info("Product deleted in Menupro Server and Odoo")
        return super(ProductTemplate, self).unlink()

    def prepare_data(self, product):
        """ Prepare data payload for menuPro api call (CREATE:post or UPDATE:patch) """

        # Get restaurant infos
        api_url = tools.config.get("api_url")
        if api_url is None:
            return "There is no API_URL in Config"

        restaurant_id = self.env['ir.config_parameter'].sudo().get_param('restaurant_id')
        if restaurant_id is None:
            return "There is no restaurant ID in Config"

        secret_key = tools.config.get("secret_key")
        if secret_key is None:
            return "There is no secret_key in Config"

        response = requests.get(api_url + restaurant_id, headers={'x-secret-key': secret_key})
        if response.status_code == 200:
            restaurant = response.json()
            name = restaurant.get('name')

            if 'description' in product and product['description'] is not False:
                description = product['description']
            else:
                description = ''

            # Prepare the data payload for menupro API
            data = {
                'title': product['name'],
                'price': product['list_price'],
                'description': description,
                'restaurantId': self.env['ir.config_parameter'].sudo().get_param('restaurant_id'),
                'restaurantName': name,
                'synchronizeOdoo': datetime.today().isoformat()
            }
            return data
        else:
            return "There is a problem while getting restaurant Info"

    def get_s3_signed_url(self, image, id_menu):
        get_signedurl_url = tools.config.get('get_signedurl_menu_url') + '?menuPicName=' + image + '&idMenu=' + id_menu
        if not get_signedurl_url:
            raise UserError("There is no signed url in Config")

        # Replace with your actual API endpoint and parameters
        response = requests.get(get_signedurl_url)
        response.raise_for_status()
        return response.json()

    def upload_image_to_s3(self, image_data, image_type, signed_url, odoo_secret_key):
        headers = {'Content-Type': f'image/{image_type}', 'x-odoo-key': odoo_secret_key}
        response = requests.put(signed_url, data=image_data, headers=headers)
        response.raise_for_status()
        return response

    def decode_image(self, image_data):
        import imghdr
        # Ensure image_data is in binary format if not already
        if isinstance(image_data, str):
            import base64
            image_data = base64.b64decode(image_data)

        # Determine the image type dynamically
        image_type = imghdr.what(None, h=image_data)
        if not image_type:
            # Handle the case where the image type cannot be determined
            raise ValueError("Could not determine image type")

        return image_data, image_type

    @api.depends('list_price', 'standard_price')
    def _compute_margin(self):
        for product in self:
            if product.type == 'consu' and product.list_price:
                product.margin = ((product.list_price - product.standard_price) / product.list_price)
            else:
                product.margin = False

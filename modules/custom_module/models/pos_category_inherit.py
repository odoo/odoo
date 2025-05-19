from odoo import models, fields, api, tools
import requests
from ..utils import image_utils


class PosCategory(models.Model):
    _inherit = 'pos.category'

    option_name = fields.Selection(selection='_fetch_categories_from_api', string='Nom de la catégorie')
    menupro_id = fields.Char(string='MenuPro ID')
    picture = fields.Char(string='Picture')
    type_name = fields.Char(string='Type Name')

    @api.model
    def _fetch_categories_from_api(self):
        """ This will be used to display the Menupro Categories to the user in a select field so the user can choose
        one of them."""
        try:
            get_level_category_url = tools.config.get('get_level_category_url')
            # Level 3 is meant for the menus categories (i.e. Burgers, Plats, Fruits de mer, Pizzas ect..)
            level = 3
            if get_level_category_url is None:
                return []

            response = requests.get(get_level_category_url + str(level))
            response.raise_for_status()
            categories = response.json()

            # Prepare a list of tuples with the category IDs and names
            category_options = [(str(category['_id']), category['menuProName']) for category in categories]
            return category_options

        except requests.exceptions.RequestException:
            return []

    def _fetch_category_data_by_id(self, category_id):
        """ This method fetch the category infos selected by the user """
        try:
            get_category_by_id = tools.config.get('get_category_by_id_url')
            if get_category_by_id is None:
                return "There is no get_category_by_id_url in Config"

            response = requests.get(get_category_by_id + str(category_id))
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException:
            return None

    def create_pos_category(self, vals):
        return super(PosCategory, self).create(vals)

    def write_pos_category(self, vals):
        return super(PosCategory, self).write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        if 'option_name' in vals_list:
            print("vals_list['option_name']", vals_list['option_name'])
            base_s3_url = tools.config.get('base_s3_url', '')
            category_data = self._fetch_category_data_by_id(vals_list['option_name'])
            category_picture = False
            if 'picture' in category_data:
                category_picture = image_utils.get_image_as_base64(base_s3_url + category_data['picture'])

            if category_data:
                vals_list.update({
                    'name': category_data['menuProName'],
                    'menupro_id': category_data['_id'],
                    'picture': base_s3_url + category_data.get('picture', ''),
                    'image_128': category_picture,
                    'type_name': category_data.get('typeName', ''),
                })
        return super(PosCategory, self).create(vals_list)

    def write(self, vals):
        if 'option_name' in vals:
            category_data = self._fetch_category_data_by_id(vals['option_name'])

            category_picture = False
            if 'picture' in category_data:
                base_s3_url = tools.config.get('base_s3_url')
                category_picture = image_utils.get_image_as_base64(base_s3_url + category_data['picture'])

            if category_data:
                vals.update({
                    'name': category_data['menuProName'],
                    'menupro_id': category_data['_id'],
                    'picture': category_data.get('picture', ''),
                    'image_128': category_picture,
                    'type_name': category_data.get('typeName', ''),
                })
        return super(PosCategory, self).write(vals)

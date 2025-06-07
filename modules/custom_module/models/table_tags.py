import logging
import requests
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.exceptions import ValidationError
from odoo.http import request
import re
_logger = logging.getLogger(__name__)

class TableTags(models.Model):
    _name = 'table.tags'
    _description = 'Table Tags'

    name = fields.Char(string='Nom', required=True, translate=True)
    menupro_id = fields.Char(string='MenuPro ID')
    status = fields.Char(string='Status', default='PENDING')

    @api.model
    def normalize_name(self, name):
        return re.sub(r'\s+', ' ', name.strip().lower())

    @api.model
    def create_in_odoo(self, vals):
        return super(TableTags, self).create(vals)

    @api.model_create_multi
    def create(self, vals_list):
        print('create Tag batch')
        new_records = []
        for vals in vals_list:
            name = vals.get('name')

            normalized_name = self.normalize_name(name)

            existing_tag = self.search([('name', '=', normalized_name)], limit=1)
            if existing_tag:
                raise ValidationError(f"Un tag avec le nom '{normalized_name}' existe déjà.")

            vals['name'] = normalized_name
            record = super(TableTags, self).create(vals)
            menupro_id = self.create_in_mp(normalized_name, record.id)
            record.write({'menupro_id': menupro_id})
            new_records.append(record)
        return self.browse([r.id for r in new_records])

    @staticmethod
    def create_in_mp(name, odoo_id):
        restaurant_id = request.env['ir.config_parameter'].sudo().get_param('restaurant_id')
        if not restaurant_id:
            raise UserError("There is no restaurant ID in Config")
        data = {
            'name': name,
            'odooId': odoo_id,
            'status': 'PENDING',
            'createdBy': restaurant_id
        }

        response = requests.post('https://api.menupro.tn/tags', json=data)
        print("response create", response.content)
        if response.status_code == 201:
            try:
                menupro_id = response.json().get('_id')
                if not menupro_id:
                    raise UserError(_("MenuPro ID not found in the response"))
                return menupro_id
            except requests.exceptions.JSONDecodeError:
                raise UserError(_("Invalid JSON response received from the API"))
        elif response.status_code == 400 and "already exist" in response.text:
            # Le tag existe déjà dans MenuPro, nous devons le récupérer
            existing_tag = TableTags.search_existing_tag_in_menupro(name, restaurant_id)
            if existing_tag:
                return existing_tag['_id']
            else:
                raise UserError(_("Tag exists in MenuPro but couldn't be retrieved"))
        else:
            raise UserError(_("Failed to create tag in MenuPro: %s") % response.text)


class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'

    # Associate tags to table
    tag_ids = fields.Many2many('table.tags', string='Options')


class RestaurantFloor(models.Model):
    _inherit = 'restaurant.floor'

    # Fetch the up-to-date tags from MP each time the interface is loaded
    def web_read(self, specification):
        self.fetch_tags_from_menupro()
        return super(RestaurantFloor, self).web_read(specification)

    def fetch_tags_from_menupro(self):
        restaurant_id = self.env['ir.config_parameter'].sudo().get_param('restaurant_id')
        if not restaurant_id:
            raise UserError(_("There is no restaurant ID in Config"))

        response = requests.get(f"https://api.menupro.tn/tags/byResto/{restaurant_id}")

        if response.status_code != 200:
            raise UserError(_("Failed to fetch tags from MenuPro: %s") % response.text)

        try:
            data = response.json()
            # Extract tags from the nested structure
            tags_data = data.get('tags', [])
            tag_ids = []
            for tag in tags_data:
                if isinstance(tag, dict):
                    tag_name = tag.get('name')
                    tag_id = tag.get('_id')
                    tag_status = tag.get('status')

                    if tag_id is None:
                        continue  # Skip if ID is missing

                    existing_tag = self.env['table.tags'].search([('menupro_id', '=', tag_id)], limit=1)
                    updates = {}
                    if existing_tag:
                        if tag_name and existing_tag.name != tag_name:
                            updates['name'] = tag_name
                        if tag_status and existing_tag.status != tag_status:
                            updates['status'] = tag_status

                        if updates:
                            existing_tag.sudo().write(updates)
                        tag_ids.append(existing_tag.id)
                    else:
                        if tag_name and tag_status:
                            new_tag = self.env['table.tags'].create_in_odoo({
                                'name': tag_name,
                                'menupro_id': tag_id,
                                'status': tag_status
                            })
                            tag_ids.append(new_tag.id)
                else:
                    new_tag = self.env['table.tags'].create_in_odoo({
                        'name': tag['name'],
                        'menupro_id': tag['_id'],
                        'status': tag['status']
                    })
                    tag_ids.append(new_tag.id)
            return self.env['table.tags'].browse(tag_ids)
        except requests.exceptions.JSONDecodeError:
            raise UserError(_("Invalid JSON response received from the API"))

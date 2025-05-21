from odoo import api, fields, models, _, tools
from odoo.exceptions import UserError
from odoo.http import request
import requests
from odoo import http


def prepare_data_and_create_floor_mp(name, odoo_id):
    restaurant_id = request.env['ir.config_parameter'].sudo().get_param('restaurant_id')
    odoo_secret_key = tools.config.get("odoo_secret_key")

    if not restaurant_id:
        raise UserError("There is no restaurant ID in Config")
    data = {
        'name': name,
        'odooId': odoo_id
    }

    response = requests.post('https://api.menupro.tn/restaurant-floors/' + restaurant_id, json=data, headers={'x-odoo-key': odoo_secret_key})

    if response.status_code == 201:
        try:
            menupro_id = response.json().get('_id')
            if not menupro_id:
                raise UserError(_("MenuPro ID not found in the response"))
            return menupro_id
        except requests.exceptions.JSONDecodeError:
            raise UserError(_("Invalid JSON response received from the API"))
    else:
        raise UserError(_("Failed to create floor in MenuPro: %s") % response.text)


def rename_floor_mp(menupro_id, new_name):
    try:
        odoo_secret_key = tools.config.get("odoo_secret_key")
        data = {
            "name": new_name
        }
        requests.patch('https://api.menupro.tn/restaurant-floors/' + menupro_id, json=data, headers={'x-odoo-key': odoo_secret_key})
    except Exception as e:
        print(f"Error renaming floor: {e}")


def deactivate_floor_mp(menupro_id,floor_record):
    try:
        odoo_secret_key = tools.config.get("odoo_secret_key")
        response = requests.delete(
            f'https://api.menupro.tn/restaurant-floors/delete/{menupro_id}',
            headers={'x-odoo-key': odoo_secret_key}
        )
        if response.status_code == 200:
            floor_record.sudo().write({'active': False})
        else:
            raise UserError(_("Failed to deactivate floor: %s") % response.text)
    except Exception as e:
        print(f"Error deactivating floor: {e}")


def delete_floor_mp(menupro_id):
    try:
        odoo_secret_key = tools.config.get("odoo_secret_key")
        requests.delete('https://api.menupro.tn/restaurant-floors/permanently-delete/' + menupro_id, headers={'x-odoo-key': odoo_secret_key})
    except Exception as e:
        print(f"Error deactivating floor: {e}")


def check_and_create_table_mp(name, odoo_id, seats, identifier, floor):
    restaurant_id = request.env['ir.config_parameter'].sudo().get_param('restaurant_id')
    odoo_secret_key = tools.config.get("odoo_secret_key")
    if not restaurant_id:
        raise UserError("There is no restaurant ID in Config")
    if not odoo_secret_key:
        raise UserError("There is no odoo_secret_key in Config")

    # Check if menupro_id is False or not set, then create the floor in MenuPro
    if not floor.menupro_id:
        print('Creating floor in MenuPro...')
        menupro_id = prepare_data_and_create_floor_mp(floor.name, floor.id)
        floor.sudo().write({'menupro_id': menupro_id})
    else:
        menupro_id = floor.menupro_id

    data = {
        'name': name,
        'odooId': odoo_id,
        'seats': seats,
        'identifier': identifier,
        'floorId':menupro_id,
    }

    response = requests.post('https://api.menupro.tn/restaurant-tables/' + restaurant_id, json=data, headers={'x-odoo-key': odoo_secret_key})
    print("response content => ", response.content)
    if response.status_code == 201:
        try:
            menupro_id = response.json().get('_id')
            if not menupro_id:
                raise UserError(_("MenuPro ID not found in the response"))
            return menupro_id
        except requests.exceptions.JSONDecodeError:
            raise UserError(_("Invalid JSON response received from the API"))
    else:
        raise UserError(_("Failed to create floor in MenuPro: %s") % response.text)


def update_table_mp(menupro_id, name, seats):
    try:
        odoo_secret_key = tools.config.get("odoo_secret_key")
        data = {
            "name": name,
            "seats": seats
        }
        response = requests.patch('https://api.menupro.tn/restaurant-tables/' + menupro_id, json=data, headers={'x-odoo-key': odoo_secret_key})
        print("content", response.content)
    except Exception as e:
        print(f"Error renaming floor: {e}")


def deactivate_table_mp(menupro_id):
    try:
        odoo_secret_key = tools.config.get("odoo_secret_key")
        requests.delete('https://api.menupro.tn/restaurant-tables/' + menupro_id,  headers={'x-odoo-key': odoo_secret_key})
    except Exception as e:
        print(f"Error deactivating floor: {e}")


def delete_table_mp(menupro_id):
    try:
        print("deleting table from MP...")
        odoo_secret_key = tools.config.get("odoo_secret_key")
        response = requests.delete('https://api.menupro.tn/restaurant-tables/permanently-delete/' + menupro_id,  headers={'x-odoo-key': odoo_secret_key})
        print("content", response.content)
    except Exception as e:
        print(f"Error deactivating floor: {e}")


def associate_tags_table_mp(menupro_id, tag_ids):
    try:
        print("associating tags to table in MP...")
        tags_to_add = []
        tags_to_remove = []

        for tag_id in tag_ids:
            # if tag_id[0] == 4 : tag added
            # if tag_id[0] == 3 : tag deleted
            print("tag_id", tag_id)
            tag_record = http.request.env['table.tags'].sudo().search([('id', '=', tag_id[1])])
            if tag_id[0] == 3:
                tags_to_remove.append(tag_record.menupro_id)
            if tag_id[0] == 4:
                tags_to_add.append(tag_record.menupro_id)

        data_to_add = {
            'tagIds': tags_to_add
        }

        data_to_remove = {
            'tagIds': tags_to_remove
        }

        odoo_secret_key = tools.config.get("odoo_secret_key")
        if data_to_add != {'tagIds': []}:
            response_to_add = requests.patch(f'https://api.menupro.tn/restaurant-tables/add-tags/push/{menupro_id}', json=data_to_add,  headers={'x-odoo-key': odoo_secret_key})
            print("content of adding", response_to_add.content)

        if data_to_remove != {'tagIds': []}:
            response_to_remove = requests.patch(f'https://api.menupro.tn/restaurant-tables/remove-tags/{menupro_id}', json=data_to_remove,  headers={'x-odoo-key': odoo_secret_key})
            print("content of removing", response_to_remove.content)

    except Exception as e:
        print(f"Error associating tags: {e}")


class RestaurantFloor(models.Model):
    _inherit = 'restaurant.floor'
    _description = 'Restaurant Floor'
    menupro_id = fields.Char(string='MenuPro ID')

    @api.model
    def sync_from_ui(self, name, background_color, config_id):
        result = super(RestaurantFloor, self).sync_from_ui(name, background_color, config_id)

        # Get the newly created record using its ID
        floor_record = self.browse(result['id'])
        if not floor_record.menupro_id:
            print('Creating floor in MenuPro...')
            # Synchronize with MP and get the menupro_id
            menupro_id = prepare_data_and_create_floor_mp(name, result['id'])
            floor_record.write({'menupro_id': menupro_id})
        return result

    def rename_floor(self, new_name):
        super(RestaurantFloor, self).rename_floor(new_name)
        if self.menupro_id:  # Vérifier que le MenuPro ID existe
            rename_floor_mp(self.menupro_id, new_name)
        else:
            raise UserError(_("Cannot rename floor: No associated MenuPro ID found"))

    def deactivate_floor(self, session_id):
        super(RestaurantFloor, self).deactivate_floor(session_id)
        if self.menupro_id:
            deactivate_floor_mp(self.menupro_id,self)
        self.write({'active': False})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if isinstance(vals, list):
                records = super(RestaurantFloor, self).create(vals)
                for record in records:
                    if not record.menupro_id:
                        print('Creating floor in MenuPro...')
                        menupro_id = prepare_data_and_create_floor_mp(record.name, record.id)
                        record.write({'menupro_id': menupro_id})
                return records
            else:
                new_record = super(RestaurantFloor, self).create(vals_list)
                if not new_record.menupro_id:
                    print('Creating floor in MenuPro...')
                    menupro_id = prepare_data_and_create_floor_mp(new_record.name, new_record.id)
                    new_record.write({'menupro_id': menupro_id})
                return new_record

    def write(self, vals):
        res = super(RestaurantFloor, self).write(vals)
        if 'name' in vals:
            for floor in self:
                if floor.menupro_id:
                    rename_floor_mp(floor.menupro_id, vals['name'])
        return res

    def unlink(self):
        menupro_ids = self.menupro_id
        res = super(RestaurantFloor, self).unlink()
        if res:
            for menupro_id in menupro_ids:
                delete_floor_mp(menupro_id)
        return res


class RestaurantTable(models.Model):
    _inherit = 'restaurant.table'
    _description = 'Restaurant Table'
    menupro_id = fields.Char(string='MenuPro ID')

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            floor = self.env['restaurant.floor'].sudo().browse(vals.get('floor_id'))
            menupro_id = check_and_create_table_mp(
                record.table_number, record.id, record.seats, record.identifier, floor
            )
            record.write({'menupro_id': menupro_id})
            if 'tag_ids' in vals:
                associate_tags_table_mp(record.menupro_id, vals['tag_ids'])
        return records

    def write(self, vals):
        print("vals", vals)
        res = super(RestaurantTable, self).write(vals)

        for table in self:
            if table.menupro_id:
                if 'name' in vals or 'seats' in vals:
                    table_number = vals.get('table_number', table.table_number)
                    seats = vals.get('seats', table.seats)
                    update_table_mp(table.menupro_id, table_number, seats)

                if 'active' in vals and not vals['active']:
                    deactivate_table_mp(table.menupro_id)

                if 'tag_ids' in vals:
                    associate_tags_table_mp(table.menupro_id, vals['tag_ids'])

        return res

    def unlink(self):
        menupro_ids = self.mapped('menupro_id')
        res = super(RestaurantTable, self).unlink()
        if res:
            for menupro_id in menupro_ids:
                delete_table_mp(menupro_id)
        return res


# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.tools import convert


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale.')
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment.')
    floor_ids = fields.Many2many('restaurant.floor', string='Restaurant Floors', help='The restaurant floors served by this point of sale.', copy=False)
    default_screen = fields.Selection([('tables', 'Tables'), ('register', 'Register')], string='Default Screen', default='tables')
    use_course_allocation = fields.Boolean(string="Enable Course Allocation")
    floor_plan_settings = fields.Json(string='Floor Plan Settings')
    floor_plan = fields.Json(string='Floor Plan', compute="_compute_floor_plan")

    def _get_forbidden_change_fields(self):
        forbidden_keys = super()._get_forbidden_change_fields()
        forbidden_keys.append('floor_ids')
        return forbidden_keys

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_restaurant = 'module_pos_restaurant' in vals and vals['module_pos_restaurant']
            if is_restaurant:
                if 'iface_printbill' not in vals:
                    vals['iface_printbill'] = True
                if 'show_product_images' not in vals:
                    vals['show_product_images'] = False
                if 'show_category_images' not in vals:
                    vals['show_category_images'] = False
        pos_configs = super().create(vals_list)
        for config in pos_configs:
            if config.module_pos_restaurant:
                self._setup_default_floor(config)
        return pos_configs

    def write(self, vals):
        if ('module_pos_restaurant' in vals and vals['module_pos_restaurant'] is False):
            vals['floor_ids'] = [(5, 0, 0)]

        if vals.get('module_pos_restaurant'):
            self._setup_default_floor(self)

        return super().write(vals)

    def _setup_default_floor(self, pos_config):
        if not pos_config.floor_ids:
            main_floor = self.env['restaurant.floor'].create({
                'name': pos_config.company_id.name,
                'pos_config_ids': [(4, pos_config.id)],
            })
            self.env['restaurant.table'].create({
                'table_number': 1,
                'floor_id': main_floor.id,
                'seats': 1,
                'floor_plan_layout': {'top': 100, 'left': 100, 'width': 130, 'height': 130, 'color': 'green', 'shape': 'square'},
            })

    @api.model
    def load_onboarding_bar_scenario(self, with_demo_data=True):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(cash_journal_vals={'name': 'Cash Bar', 'show_on_dashboard': False})
        config = self.env['pos.config'].create({
            'name': 'Bar',
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
            'default_screen': 'register'
        })
        self.env['ir.model.data']._update_xmlids([{
            'xml_id': self._get_suffixed_ref_name('pos_restaurant.pos_config_main_bar'),
            'record': config,
            'noupdate': True,
        }])
        if not self.env.ref('pos_restaurant.floor_main', raise_if_not_found=False):
            convert.convert_file(self._env_with_clean_context(), 'pos_restaurant', 'data/scenarios/restaurant_floor.xml', idref=None, mode='init', noupdate=True)
        config_floors = [(5, 0)]
        if (floor_main := self.env.ref('pos_restaurant.floor_main', raise_if_not_found=False)):
            config_floors += [(4, floor_main.id)]
        if (floor_patio := self.env.ref('pos_restaurant.floor_patio', raise_if_not_found=False)):
            config_floors += [(4, floor_patio.id)]
        config.update({'floor_ids': config_floors})
        config._load_bar_demo_data(with_demo_data)
        return {'config_id': config.id}

    def _load_bar_demo_data(self, with_demo_data=True):
        self.ensure_one()
        convert.convert_file(self._env_with_clean_context(), 'pos_restaurant', 'data/scenarios/bar_category_data.xml', idref=None, mode='init', noupdate=True)
        if with_demo_data:
            convert.convert_file(self._env_with_clean_context(), 'pos_restaurant', 'data/scenarios/bar_demo_data.xml', idref=None, mode='init', noupdate=True)
        bar_categories = self.get_record_by_ref([
            'pos_restaurant.pos_category_cocktails',
            'pos_restaurant.pos_category_soft_drinks',
        ])
        if bar_categories:
            self.limit_categories = True
            self.iface_available_categ_ids = bar_categories

    @api.model
    def load_onboarding_restaurant_scenario(self, with_demo_data=True):
        journal, payment_methods_ids = self._create_journal_and_payment_methods(cash_journal_vals={'name': _('Cash Restaurant'), 'show_on_dashboard': False})
        presets = self.get_record_by_ref([
            'pos_restaurant.pos_takein_preset',
            'pos_restaurant.pos_takeout_preset',
            'pos_restaurant.pos_delivery_preset',
        ]) + self.env['pos.preset'].search([]).ids
        config = self.env['pos.config'].create({
            'name': _('Restaurant'),
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
            'use_presets': bool(presets),
            'default_preset_id': presets[0] if presets else False,
            'available_preset_ids': [(6, 0, presets)],
        })
        self.env['ir.model.data']._update_xmlids([{
            'xml_id': self._get_suffixed_ref_name('pos_restaurant.pos_config_main_restaurant'),
            'record': config,
            'noupdate': True,
        }])
        if bool(presets):
            # Ensure the "Presets" menu is visible when installing the restaurant scenario
            self.env.ref("point_of_sale.group_pos_preset").implied_by_ids |= self.env.ref("base.group_user")
        if not self.env.ref('pos_restaurant.floor_main', raise_if_not_found=False):
            convert.convert_file(self._env_with_clean_context(), 'pos_restaurant', 'data/scenarios/restaurant_floor.xml', idref=None, mode='init', noupdate=True)
        config_floors = [(5, 0)]
        if (floor_main := self.env.ref('pos_restaurant.floor_main', raise_if_not_found=False)):
            config_floors += [(4, floor_main.id)]
        if (floor_patio := self.env.ref('pos_restaurant.floor_patio', raise_if_not_found=False)):
            config_floors += [(4, floor_patio.id)]
        config.update({'floor_ids': config_floors})
        config._load_restaurant_demo_data(with_demo_data)
        existing_session = self.env.ref('pos_restaurant.pos_closed_session_3', raise_if_not_found=False)
        if with_demo_data and self.env.company.id == self.env.ref('base.main_company').id and not existing_session:
            convert.convert_file(self._env_with_clean_context(), 'pos_restaurant', 'data/scenarios/restaurant_demo_session.xml', idref=None, mode='init', noupdate=True)
        return {'config_id': config.id}

    @api.depends('floor_plan_settings')
    def _compute_local_data_integrity(self):
        super()._compute_local_data_integrity()

    def _load_restaurant_demo_data(self, with_demo_data=True):
        self.ensure_one()
        convert.convert_file(self._env_with_clean_context(), 'pos_restaurant', 'data/scenarios/restaurant_category_data.xml', idref=None, mode='init', noupdate=True)
        if with_demo_data:
            convert.convert_file(self._env_with_clean_context(), 'pos_restaurant', 'data/scenarios/restaurant_demo_data.xml', idref=None, mode='init', noupdate=True)
        restaurant_categories = self.get_record_by_ref([
            'pos_restaurant.food',
            'pos_restaurant.drinks',
        ])
        if restaurant_categories:
            self.limit_categories = True
            self.iface_available_categ_ids = restaurant_categories

    def _get_demo_data_loader_methods(self):
        mapping = super()._get_demo_data_loader_methods()
        mapping.update({
            'pos_restaurant.pos_config_main_restaurant': self._load_restaurant_demo_data,
            'pos_restaurant.pos_config_main_bar': self._load_bar_demo_data,
        })
        return mapping

    def _get_default_demo_data_xml_id(self):
        if self.module_pos_restaurant:
            return 'pos_restaurant.pos_config_main_restaurant'
        return super()._get_default_demo_data_xml_id()

    def _compute_floor_plan(self):
        for record in self:
            if not record.module_pos_restaurant:
                record.floor_plan = None
                continue
            record.floor_plan = {
                'settings': record.floor_plan_settings or {},
                'floors': [
                    {
                        'id': floor.id,
                        **(floor.floor_plan_layout or {}),
                        'tables': [
                            {'id': table.id, **(table.floor_plan_layout or {})}
                            for table in floor.table_ids if table.active
                        ]
                    }
                    for floor in record.floor_ids if floor.active
                ],
            }

    def get_floor_plan(self):
        self.ensure_one()
        return {
            'config': {
                'floor_plan': self.floor_plan,
                'floor_ids': self.floor_ids.ids,
            },
            'records': {
                'restaurant.floor': self.env['restaurant.floor']._load_pos_data_read(self.floor_ids, self),
                'restaurant.table': self.env['restaurant.table']._load_pos_data_read(self.floor_ids.table_ids, self),
            }
        }

    def save_floor_plan(self, floor_plan):
        self.ensure_one()
        existing_floors = {f.id: f for f in self.floor_ids if f.active}
        existing_tables = {t.id: t for t in self.floor_ids.table_ids if t.active}
        seen_floor_ids = set()
        seen_table_ids = set()
        session_id = self.current_session_id.id

        for floor_data in floor_plan.get("floors", []):
            floor = self._save_floor_plan_floor(floor_data, existing_floors)
            if not floor:
                continue
            seen_floor_ids.add(floor.id)

            for table_data in floor_data.get("tables", []):
                table = self._save_floor_plan_table(table_data, floor, existing_tables)
                if table:
                    seen_table_ids.add(table.id)

        self.floor_plan_settings = floor_plan.get("settings", {})

        # Deactivate removed floors and tables
        for floor_id, floor in existing_floors.items():
            if floor_id not in seen_floor_ids:
                floor.deactivate_floor(session_id)

        for table_id, table in existing_tables.items():
            if table_id not in seen_table_ids:
                table.are_orders_still_in_draft()
                table.active = False

        config_ids = self.floor_ids.pos_config_ids

        for config in config_ids:
            config._notify("FLOOR_PLAN_UPD", {
                'device_identifier': self.env.context.get('device_identifier', False),
                'session_id': session_id
            })

        return self.get_floor_plan()

    def _save_floor_plan_floor(self, floor_data, existing_floors):
        self.ensure_one()
        floor_id = floor_data.get("id")
        model_data, layout_data = self._split_layout_server_data(floor_data, {"name"}, {"id", "tables", "newImages"})
        if floor_id:
            floor = existing_floors.get(floor_id)
            if not floor:
                return None
            floor.write({**model_data})
        else:
            floor = self.env['restaurant.floor'].create({
                **model_data,
                "pos_config_ids": [(4, self.id)],
            })

        def is_valid_floor_image(att):
            return (
                    att.exists()
                    and att.res_model == 'restaurant.floor'
                    and not att.res_field
            )

        IrAttachment = self.env['ir.attachment']
        floor_image_ids = set(IrAttachment.search([
            ('res_model', '=', 'restaurant.floor'),
            ('res_id', '=', floor.id),
        ]).ids)

        # Create new attachment for newly uploaded images and link them to the floor
        new_image_ids = floor_data.get("newImages", [])
        attachments = IrAttachment.browse(new_image_ids)
        for attachment in attachments:
            if is_valid_floor_image(attachment) and not attachment.res_id:
                attachment.res_id = floor.id
                floor_image_ids.add(attachment.id)

        # Decoration images
        decoration_images = []
        for decoration in layout_data.get('decorations', []):
            if decoration.get('id') and decoration.get("shape") == "image":
                decoration_images.append(decoration)

        # Background image
        bg_image = layout_data.get('bgImage')
        if bg_image and bg_image.get('id'):
            decoration_images.append(bg_image)

        # If the same image is used in different floor we need to duplicate it and assign the correct res_id
        for image in decoration_images:
            image_id = image.get('id')
            if image_id in floor_image_ids:
                continue

            attachment = IrAttachment.browse(image_id)
            if is_valid_floor_image(attachment):
                new_attachment = attachment.copy({"res_id": floor.id})
                floor_image_ids.add(new_attachment.id)
                image["id"] = new_attachment.id

        floor.floor_plan_layout = layout_data
        return floor

    def _save_floor_plan_table(self, table_data, floor, existing_tables):
        self.ensure_one()
        table_id = table_data.get("id")
        model_data, layout_data = self._split_layout_server_data(table_data, {"table_number", "seats"}, {"id"})
        if table_id:
            table = existing_tables.get(table_id)
            if not table:
                return None
            table.write({**model_data, "floor_plan_layout": layout_data})
        else:
            table = self.env['restaurant.table'].create({
                **model_data,
                "floor_id": floor.id,
                "floor_plan_layout": layout_data,
            })

        return table

    @api.model
    def _split_layout_server_data(self, data, model_keys, layout_exclude_keys):
        layout_exclude = set(layout_exclude_keys) | set(model_keys)
        model_data = {k: data[k] for k in model_keys if k in data}
        layout_data = {k: v for k, v in data.items() if k not in layout_exclude}
        return model_data, layout_data

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import convert


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale.')
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment.')
    floor_ids = fields.Many2many('restaurant.floor', string='Restaurant Floors', help='The restaurant floors served by this point of sale.', copy=False)
    default_screen = fields.Selection([('tables', 'Tables'), ('register', 'Register')], string='Default Screen', default='tables')

    def _get_forbidden_change_fields(self):
        forbidden_keys = super(PosConfig, self)._get_forbidden_change_fields()
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
            if not is_restaurant:
                vals['set_tip_after_payment'] = False
        pos_configs = super().create(vals_list)
        for config in pos_configs:
            if config.module_pos_restaurant:
                self._setup_default_floor(config)
        return pos_configs

    def write(self, vals):
        if ('module_pos_restaurant' in vals and vals['module_pos_restaurant'] is False):
            vals['floor_ids'] = [(5, 0, 0)]

        if 'module_pos_restaurant' in vals and not vals['module_pos_restaurant']:
            vals['set_tip_after_payment'] = False
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
                'position_h': 100,
                'position_v': 100,
                'width': 130,
                'height': 130,
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

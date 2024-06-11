# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import json
from collections import defaultdict


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale.')
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment.')
    iface_orderline_notes = fields.Boolean(string='Internal Notes', help='Allow custom Internal notes on Orderlines.')
    floor_ids = fields.Many2many('restaurant.floor', string='Restaurant Floors', help='The restaurant floors served by this point of sale.')
    set_tip_after_payment = fields.Boolean('Set Tip After Payment', help="Adjust the amount authorized by payment terminals to add a tip after the customers left or at the end of the day.")
    module_pos_restaurant = fields.Boolean(default=True)
    module_pos_restaurant_appointment = fields.Boolean("Table Booking")

    def get_tables_order_count_and_printing_changes(self):
        self.ensure_one()
        floors = self.env['restaurant.floor'].search([('pos_config_ids', '=', self.id)])
        tables = self.env['restaurant.table'].search([('floor_id', 'in', floors.ids)])
        domain = [('state', '=', 'draft'), ('table_id', 'in', tables.ids)]

        order_stats = self.env['pos.order']._read_group(domain, ['table_id'], ['__count'])
        linked_orderlines = self.env['pos.order.line'].search([('order_id.state', '=', 'draft'), ('order_id.table_id', 'in', tables.ids)])
        orders_map = {table.id: count for table, count in order_stats}
        changes_map = defaultdict(lambda: 0)
        skip_changes_map = defaultdict(lambda: 0)

        for line in linked_orderlines:
            # For the moment, as this feature is not compatible with pos_self_order,
            # we ignore last_order_preparation_change when it is set to false.
            # In future, pos_self_order will send the various changes to the order.
            if not line.order_id.last_order_preparation_change:
                line.order_id.last_order_preparation_change = '{}'

            last_order_preparation_change = json.loads(line.order_id.last_order_preparation_change)
            prep_change = {}
            for line_uuid in last_order_preparation_change:
                prep_change[last_order_preparation_change[line_uuid]['line_uuid']] = last_order_preparation_change[line_uuid]
            quantity_changed = 0
            if line.uuid in prep_change:
                quantity_changed = line.qty - prep_change[line.uuid]['quantity']
            else:
                quantity_changed = line.qty

            if line.skip_change:
                skip_changes_map[line.order_id.table_id.id] += quantity_changed
            else:
                changes_map[line.order_id.table_id.id] += quantity_changed

        result = []
        for table in tables:
            result.append({'id': table.id, 'orders': orders_map.get(table.id, 0), 'changes': changes_map.get(table.id, 0), 'skip_changes': skip_changes_map.get(table.id, 0)})
        return result

    def _get_forbidden_change_fields(self):
        forbidden_keys = super(PosConfig, self)._get_forbidden_change_fields()
        forbidden_keys.append('floor_ids')
        return forbidden_keys

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_restaurant = 'module_pos_restaurant' not in vals or vals['module_pos_restaurant']
            if is_restaurant and 'iface_splitbill' not in vals:
                vals['iface_splitbill'] = True
            if not is_restaurant or not vals.get('iface_tipproduct', False):
                vals['set_tip_after_payment'] = False
        pos_configs = super().create(vals_list)
        for config in pos_configs:
            if config.module_pos_restaurant:
                self._setup_default_floor(config)
        return pos_configs

    def write(self, vals):
        if ('module_pos_restaurant' in vals and vals['module_pos_restaurant'] is False):
            vals['floor_ids'] = [(5, 0, 0)]

        if ('module_pos_restaurant' in vals and not vals['module_pos_restaurant']) or ('iface_tipproduct' in vals and not vals['iface_tipproduct']):
            vals['set_tip_after_payment'] = False

        if ('module_pos_restaurant' in vals and vals['module_pos_restaurant']):
            self._setup_default_floor(self)

        return super().write(vals)

    @api.model
    def post_install_pos_localisation(self, companies=False):
        self = self.sudo()
        if not companies:
            companies = self.env['res.company'].search([])
        super(PosConfig, self).post_install_pos_localisation(companies)
        for company in companies.filtered('chart_template'):
            pos_configs = self.search([
                *self.env['account.journal']._check_company_domain(company),
                ('module_pos_restaurant', '=', True),
            ])
            if not pos_configs:
                pos_configs = self.env['pos.config'].with_company(company).create({
                'name': _('Bar'),
                'company_id': company.id,
                'module_pos_restaurant': True,
                'iface_splitbill': True,
                'iface_printbill': True,
                'iface_orderline_notes': True,

            })
            pos_configs.setup_defaults(company)

    def setup_defaults(self, company):
        main_restaurant = self.env.ref('pos_restaurant.pos_config_main_restaurant', raise_if_not_found=False)
        main_restaurant_is_present = main_restaurant and self.filtered(lambda cfg: cfg.id == main_restaurant.id)
        if main_restaurant_is_present:
            non_main_restaurant_configs = self - main_restaurant
            non_main_restaurant_configs.assign_payment_journals(company)
            main_restaurant._setup_main_restaurant_defaults()
            self.generate_pos_journal(company)
            self.setup_invoice_journal(company)
        else:
            super().setup_defaults(company)

    def _setup_main_restaurant_defaults(self):
        self.ensure_one()
        self._link_same_non_cash_payment_methods_if_exists('point_of_sale.pos_config_main')
        self._ensure_cash_payment_method('MRCSH', _('Cash Restaurant'))
        self._archive_shop()

    def _archive_shop(self):
        shop = self.env.ref('point_of_sale.pos_config_main', raise_if_not_found=False)
        if shop:
            session_count = self.env['pos.session'].search_count([('config_id', '=', shop.id)])
            if session_count == 0:
                shop.update({'active': False})

    def _setup_default_floor(self, pos_config):
        if not pos_config.floor_ids:
            main_floor = self.env['restaurant.floor'].create({
                'name': pos_config.company_id.name,
                'pos_config_ids': [(4, pos_config.id)],
            })
            self.env['restaurant.table'].create({
                'name': '1',
                'floor_id': main_floor.id,
                'seats': 1,
                'position_h': 100,
                'position_v': 100,
                'width': 100,
                'height': 100,
            })

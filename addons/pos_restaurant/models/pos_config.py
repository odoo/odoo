# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import json
from collections import defaultdict
from odoo.tools import convert


class PosConfig(models.Model):
    _inherit = 'pos.config'

    iface_splitbill = fields.Boolean(string='Bill Splitting', help='Enables Bill Splitting in the Point of Sale.')
    iface_printbill = fields.Boolean(string='Bill Printing', help='Allows to print the Bill before payment.')
    floor_ids = fields.Many2many('restaurant.floor', string='Restaurant Floors', help='The restaurant floors served by this point of sale.')
    set_tip_after_payment = fields.Boolean('Set Tip After Payment', help="Adjust the amount authorized by payment terminals to add a tip after the customers left or at the end of the day.")
    module_pos_restaurant_appointment = fields.Boolean("Table Booking")
    takeaway = fields.Boolean("Takeaway", help="Allow to create orders for takeaway customers.")
    takeaway_fp_id = fields.Many2one(
        'account.fiscal.position',
        string='Alternative Fiscal Position',
        help='This is useful for restaurants with onsite and take-away services that imply specific tax rates.',
    )

    def _get_forbidden_change_fields(self):
        forbidden_keys = super(PosConfig, self)._get_forbidden_change_fields()
        forbidden_keys.append('floor_ids')
        return forbidden_keys

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            is_restaurant = 'module_pos_restaurant' in vals and vals['module_pos_restaurant']
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

    def _create_takeaway_fiscal_position(self, config):
        tax_21 = self.env.ref(f'account.{self.env.company.id}_attn_VAT-OUT-21-L')
        tax_12 = self.env.ref(f'account.{self.env.company.id}_attn_VAT-OUT-12-L')
        tax_6 = self.env.ref(f'account.{self.env.company.id}_attn_VAT-OUT-06-L')

        fp = self.env['account.fiscal.position'].create({
            'name': 'Take out',
        })
        self.env['account.fiscal.position.tax'].create({
            'tax_src_id': tax_21.id,
            'tax_dest_id': tax_6.id,
            'position_id': fp.id
        })
        self.env['account.fiscal.position.tax'].create({
            'tax_src_id': tax_12.id,
            'tax_dest_id': tax_6.id,
            'position_id': fp.id
        })
        config.write({'takeaway': True, 'takeaway_fp_id': fp.id})

    @api.model
    def _load_bar_data(self):
        convert.convert_file(self.env, 'pos_restaurant', 'data/scenarios/bar_data.xml', None, noupdate=True, mode='init', kind='data')

    @api.model
    def _load_restaurant_data(self):
        convert.convert_file(self.env, 'pos_restaurant', 'data/scenarios/restaurant_data.xml', None, noupdate=True, mode='init', kind='data')

    def _create_tax_alcohol(self):
        """Create the 'tax_alcohol' if it doesn't already exist."""
        tax_ref = 'pos_restaurant.tax_alcohol_luxury'
        tax = self.env.ref(tax_ref, raise_if_not_found=False)
        if not tax:
            tax = self.env['account.tax'].create({
                'name': '21% Alcohol / luxury',
                'description': '21% VAT (Alcohol, luxury)',
                'amount': 21,
                'amount_type': 'percent',
                'type_tax_use': 'sale',
            })
            self.env['ir.model.data']._update_xmlids([{
                'xml_id': tax_ref,
                'record': tax,
                'noupdate': True,
            }])
        return tax

    def _is_belgian_fp_company(self):
        return self.env['ir.module.module'].search_count([('name', '=', 'l10n_be')]) > 0 and \
            self.env['account.fiscal.position'].search_count([
                ('company_id', '=', self.env.company.id),
                ('country_id.code', '=', 'BE')
            ]) > 0

    @api.model
    def load_onboarding_bar_scenario(self):
        ref_name = 'pos_restaurant.pos_config_main_bar'
        if not self.env.ref(ref_name, raise_if_not_found=False):
            self._load_bar_data()
        journal, payment_methods_ids = self._create_journal_and_payment_methods(cash_journal_vals={'name': 'Cash Bar', 'show_on_dashboard': False})
        bar_categories = self.get_categories([
            'pos_restaurant.pos_category_cocktails',
            'pos_restaurant.pos_category_soft_drinks',
        ])
        config = self.env['pos.config'].create({
            'name': 'Bar',
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids,
            'limit_categories': True,
            'iface_available_categ_ids': bar_categories,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
        })
        if self._is_belgian_fp_company():
            tax_alcohol = self._create_tax_alcohol()
            self.env['product.template'].search([('pos_categ_ids', 'in', [self.env.ref('pos_restaurant.pos_category_cocktails').id])]).write({'taxes_id': tax_alcohol})
        self.env['ir.model.data']._update_xmlids([{
            'xml_id': self._get_suffixed_ref_name(ref_name),
            'record': config,
            'noupdate': True,
        }])

    @api.model
    def load_onboarding_restaurant_scenario(self):
        ref_name = 'pos_restaurant.pos_config_main_restaurant'
        if not self.env.ref(ref_name, raise_if_not_found=False):
            self._load_restaurant_data()

        journal, payment_methods_ids = self._create_journal_and_payment_methods(cash_journal_vals={'name': 'Cash Restaurant', 'show_on_dashboard': False})
        restaurant_categories = self.get_categories([
            'pos_restaurant.food',
            'pos_restaurant.drinks',
        ])
        config = self.env['pos.config'].create({
            'name': _('Restaurant'),
            'company_id': self.env.company.id,
            'journal_id': journal.id,
            'payment_method_ids': payment_methods_ids,
            'limit_categories': True,
            'iface_available_categ_ids': restaurant_categories,
            'iface_splitbill': True,
            'module_pos_restaurant': True,
        })
        if self._is_belgian_fp_company():
            self._create_tax_alcohol()
            self._create_takeaway_fiscal_position(config)

        self.env['ir.model.data']._update_xmlids([{
            'xml_id': self._get_suffixed_ref_name(ref_name),
            'record': config,
            'noupdate': True,
        }])
        if self.env.company.id == self.env.ref('base.main_company').id:
            existing_session = self.env.ref('pos_restaurant.pos_closed_session_3', raise_if_not_found=False)
            if not existing_session:
                convert.convert_file(self.env, 'pos_restaurant', 'data/restaurant_session_floor.xml', None, noupdate=True, mode='init', kind='data')



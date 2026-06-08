# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval
import random

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PosCategory(models.Model):
    _name = 'pos.category'
    _description = "Point of Sale Category"
    _inherit = ['pos.load.mixin']
    _rec_name = 'complete_name'
    _order = "sequence, name"

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if self._has_cycle():
            raise ValidationError(_('Error! You cannot create recursive categories.'))

    def get_default_color(self):
        return random.randint(0, 10)

    def _default_sequence(self):
        return (self.search([], order="sequence desc", limit=1).sequence or 0) + 1

    name = fields.Char(string='Category Name', required=True, translate=True)
    complete_name = fields.Char('Complete Name', compute='_compute_complete_name', recursive=True, store=True)
    parent_id = fields.Many2one('pos.category', string='Parent Category', index=True)
    child_ids = fields.One2many('pos.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of product categories.", default=_default_sequence)
    image_512 = fields.Image("Image", max_width=512, max_height=512)
    image_128 = fields.Image("Image 128", related="image_512", max_width=128, max_height=128, store=True)
    color = fields.Integer('Color', required=False, default=get_default_color)
    hour_until = fields.Float(string='Availability Until', default=24.0, help="The product will be available until this hour for online order and self order.")
    hour_after = fields.Float(string='Availability After', default=0.0, help="The product will be available after this hour for online order and self order.")
    pos_config_ids = fields.Many2many('pos.config', string='Linked PoS Configurations')

    # During loading of data, the image is not loaded so we expose a lighter
    # field to determine whether a pos.category has an image or not.
    has_image = fields.Boolean(compute='_compute_has_image')
    product_count = fields.Integer(compute="_compute_product_count")

    @api.model
    def _load_pos_data_domain(self, data, config):
        domain = []
        if config.limit_categories:
            preparation_categories = [printer['product_categories_ids'] for printer in data['pos.printer']]
            flattened_preparation_categories = [item for sublist in preparation_categories for item in sublist]
            domain += [('id', 'in', flattened_preparation_categories + config.iface_available_categ_ids.ids)]
        return domain

    @api.model
    def _load_pos_data_fields(self, config):
        return ['id', 'name', 'parent_id', 'child_ids', 'write_date', 'has_image', 'color', 'sequence', 'hour_until', 'hour_after']

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for category in self:
            if category.parent_id:
                category.complete_name = '%s / %s' % (category.parent_id.complete_name, category.name)
            else:
                category.complete_name = category.name

    @api.ondelete(at_uninstall=False)
    def _unlink_except_session_open(self):
        for record in self:
            if record.pos_config_ids:
                raise UserError(_('You cannot delete a category which is currently in use in a point of sale.'))

    @api.depends('has_image')
    def _compute_has_image(self):
        for category in self:
            category.has_image = bool(category.image_128)

    def _get_descendants(self):
        available_categories = self
        for child in self.child_ids:
            available_categories |= child
            available_categories |= child._get_descendants()
        return available_categories

    def _get_parents(self):
        available_categories = self
        if self.parent_id:
            available_categories |= self.parent_id
            available_categories |= self.parent_id._get_parents()
        return available_categories

    @api.constrains('hour_until', 'hour_after')
    def _check_hour(self):
        for category in self:
            if category.hour_until and not (0.0 <= category.hour_until <= 24.0):
                raise ValidationError(_('The Availability Until must be set between 00:00 and 24:00'))
            if category.hour_after and not (0.0 <= category.hour_after <= 24.0):
                raise ValidationError(_('The Availability After must be set between 00:00 and 24:00'))
            if category.hour_until and category.hour_after and category.hour_until < category.hour_after:
                raise ValidationError(_('The Availability Until must be greater than Availability After.'))

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if 'name' not in default:
            for pos_category, vals in zip(self, vals_list):
                vals['name'] = _("%s (copy)", pos_category.name)
        return vals_list

    def _compute_product_count(self):
        all_categories = self.search_fetch(
            [('id', 'child_of', self.ids)],
            ['parent_id'],
        )
        product_data = self.env['product.template']._read_group(
            [('pos_categ_ids', 'in', all_categories.ids)],
            ['pos_categ_ids'],
            ['id:array_agg'],
        )
        self_ids = set(self._ids)
        category_products = {categ.id: set() for categ in self}
        for categ, product_ids in product_data:
            while categ:
                if categ.id in self_ids:
                    category_products[categ.id].update(product_ids)
                categ = categ.parent_id
        for categ in self:
            categ.product_count = len(category_products[categ.id])

    def action_open_associated_products(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('point_of_sale.product_template_action_pos_product')
        action['context'] = dict(
            literal_eval(action.get('context', '{}')),
            search_default_pos_categ_ids=[self.id],
            default_pos_categ_ids=[self.id]
        )
        action['views'] = [(False, 'kanban'), (False, 'list'), (False, 'form')]
        return action

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import List, Tuple
import random

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PosCategory(models.Model):
    _name = 'pos.category'
    _description = "Point of Sale Category"
    _inherit = ['pos.load.mixin']
    _order = "sequence, name"

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if self._has_cycle():
            raise ValidationError(_('Error! You cannot create recursive categories.'))

    def get_default_color(self):
        return random.randint(0, 10)

    name = fields.Char(string='Category Name', required=True, translate=True)
    parent_id = fields.Many2one('pos.category', string='Parent Category', index=True)
    child_ids = fields.One2many('pos.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of product categories.")
    image_128 = fields.Image("Image", max_width=128, max_height=128)
    color = fields.Integer('Color', required=False, default=get_default_color)
    hour_until = fields.Float(string='Availability Until', default=24.0, help="The product will be available until this hour for online order and self order.")
    hour_after = fields.Float(string='Availability After', default=0.0, help="The product will be available after this hour for online order and self order.")

    # During loading of data, the image is not loaded so we expose a lighter
    # field to determine whether a pos.category has an image or not.
    has_image = fields.Boolean(compute='_compute_has_image')

    @api.model
    def _load_pos_data_domain(self, data):
        domain = []
        limited_categories = data['pos.config'][0]['limit_categories']
        if limited_categories:
            available_category_ids = data['pos.config'][0]['iface_available_categ_ids']
            category_ids = self.env['pos.category'].browse(available_category_ids)._get_descendants().ids
            domain += [('id', 'in', category_ids)]
        return domain

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'parent_id', 'child_ids', 'write_date', 'has_image', 'color', 'sequence', 'hour_until', 'hour_after']

    def _get_hierarchy(self) -> List[str]:
        """ Returns a list representing the hierarchy of the categories. """
        self.ensure_one()
        return (self.parent_id._get_hierarchy() if self.parent_id else []) + [(self.name or '')]

    @api.depends('parent_id')
    def _compute_display_name(self):
        for cat in self:
            cat.display_name = " / ".join(cat._get_hierarchy())

    @api.ondelete(at_uninstall=False)
    def _unlink_except_session_open(self):
        if self.search_count([('id', 'in', self.ids)]):
            if self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')]):
                raise UserError(_('You cannot delete a point of sale category while a session is still opened.'))

    @api.depends('has_image')
    def _compute_has_image(self):
        for category in self:
            category.has_image = bool(category.image_128)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("parent_id"):
                vals["color"] = self.search_read([("id", "=", vals["parent_id"])])[0][
                    "color"
                ]
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('parent_id') and not ("color" in vals):
            vals["color"] = self.search_read([("id", "=", vals["parent_id"])])[0][
                "color"
            ]
        return super().write(vals)

    def _get_descendants(self):
        available_categories = self
        for child in self.child_ids:
            available_categories |= child
            available_categories |= child._get_descendants()
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

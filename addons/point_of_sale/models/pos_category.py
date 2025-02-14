# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import List, Tuple
import random

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PosCategory(models.Model):
    _name = "pos.category"
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

    # During loading of data, the image is not loaded so we expose a lighter
    # field to determine whether a pos.category has an image or not.
    has_image = fields.Boolean(compute='_compute_has_image')

    @api.model
    def _load_pos_data_domain(self, data):
        config_id = self.env['pos.config'].browse(data['pos.config']['data'][0]['id'])
        domain = [('id', 'in', config_id._get_available_categories().ids)] if config_id.limit_categories and config_id.iface_available_categ_ids else []
        return domain

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'parent_id', 'child_ids', 'write_date', 'has_image', 'color', 'sequence']

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

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import List, Tuple

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class PosCategory(models.Model):
    _name = "pos.category"
    _description = "Point of Sale Category"
    _order = "sequence, name"

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error! You cannot create recursive categories.'))

    name = fields.Char(string='Category Name', required=True, translate=True)
    parent_id = fields.Many2one('pos.category', string='Parent Category', index=True)
    child_id = fields.One2many('pos.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of product categories.")
    image_128 = fields.Image("Image", max_width=128, max_height=128)

    # During loading of data, the image is not loaded so we expose a lighter
    # field to determine whether a pos.category has an image or not.
    has_image = fields.Boolean(compute='_compute_has_image')

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

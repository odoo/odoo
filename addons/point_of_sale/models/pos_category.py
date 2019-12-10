# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class PosCategory(models.Model):
    _name = "pos.category"
    _description = "Point of Sale Category"
    _order = "sequence, name"

    @api.constrains('parent_id')
    def _check_category_recursion(self):
        if not self._check_recursion():
            raise ValidationError(_('Error ! You cannot create recursive categories.'))

    name = fields.Char(string='Category Name', required=True, translate=True)
    parent_id = fields.Many2one('pos.category', string='Parent Category', index=True)
    child_id = fields.One2many('pos.category', 'parent_id', string='Children Categories')
    sequence = fields.Integer(help="Gives the sequence order when displaying a list of product categories.")
    image_128 = fields.Image("Image", max_width=128, max_height=128)

    def name_get(self):
        def get_names(cat):
            res = []
            while cat:
                res.append(cat.name)
                cat = cat.parent_id
            return res
        return [(cat.id, " / ".join(reversed(get_names(cat)))) for cat in self]

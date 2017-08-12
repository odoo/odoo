# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ResLang(models.Model):

    _inherit = 'res.lang'

    default_uom_ids = fields.Many2many(
        string='Default Units',
        comodel_name='product.uom',
    )

    @api.multi
    @api.constrains('default_uom_ids')
    def _check_default_uom_ids(self):
        for record in self:
            categories = set(record.default_uom_ids.mapped('category_id'))
            if len(categories) != len(record.default_uom_ids):
                raise ValidationError(_(
                    'Only one default unit of measure per category may '
                    'be selected.',
                ))

    @api.model
    def default_uom_by_category(self, category_name, lang=None):
        """Return the default UoM for language for the input UoM Category.
        Args:
            category_name (str): Name of the UoM category to get the default
            for.
            lang (ResLang or str, optional): Recordset or code of the language
            to get the default for. Will use the current user language if
            omitted.
        Returns:
            ProductUom: Unit of measure representing the default, if set.
            Empty recordset otherwise.
        """
        if lang is None:
            lang = self.env.user.lang
        if isinstance(lang, basestring):
            lang = self.env['res.lang'].search([
                ('code', '=', lang),
            ],
                limit=1,
            )
        results = lang.default_uom_ids.filtered(
            lambda r: r.category_id.name == category_name,
        )
        return results[:1]

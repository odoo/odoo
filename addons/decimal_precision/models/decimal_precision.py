# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, tools


class DecimalPrecision(models.Model):
    _name = 'decimal.precision'

    name = fields.Char('Usage', index=True, required=True)
    digits = fields.Integer('Digits', required=True, default=2)

    _sql_constraints = [
        ('name_uniq', 'unique (name)', """Only one value can be defined for each given usage!"""),
    ]

    @api.model
    @tools.ormcache('application')
    def precision_get(self, application):
        res = self.search([('name', '=', application)], limit=1).digits
        return res if res else 2

    def clear_cache(self):
        """ Deprecated, use `clear_caches` instead. """
        self.clear_caches()

    @api.model
    def create(self, vals):
        res = super(DecimalPrecision, self).create(vals)
        self.clear_caches()
        return res

    @api.multi
    def unlink(self):
        res = super(DecimalPrecision, self).unlink()
        self.clear_caches()
        return res

    @api.multi
    def write(self, vals):
        res = super(DecimalPrecision, self).write(vals)
        self.clear_caches()
        return res

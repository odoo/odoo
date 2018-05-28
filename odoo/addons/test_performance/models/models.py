# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class BaseModel(models.Model):
    _name = 'test_performance.base'

    name = fields.Char()
    value = fields.Integer()
    value_pc = fields.Float(compute="_value_pc", store=True)
    partner_id = fields.Many2one('res.partner', string='Customer')

    line_ids = fields.One2many('test_performance.line', 'base_id')
    total = fields.Integer(compute="_total", store=True)
    tag_ids = fields.Many2many('test_performance.tag')

    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value_pc = float(record.value) / 100

    @api.depends('line_ids.value')
    def _total(self):
        for record in self:
            record.total = sum(line.value for line in record.line_ids)


class LineModel(models.Model):
    _name = 'test_performance.line'

    base_id = fields.Many2one('test_performance.base', required=True, ondelete='cascade')
    value = fields.Integer()


class TagModel(models.Model):
    _name = 'test_performance.tag'

    name = fields.Char()

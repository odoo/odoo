# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class BaseModel(models.Model):
    _name = 'test_complete_field.model'
    _description = 'Base Model'

    boolean_field = fields.Boolean()
    integer_field = fields.Integer()
    float_field = fields.Float()
    char_field = fields.Char()
    selection_field = fields.Selection([('draft', 'New'), ('done', 'Done')])
    m2o_field = fields.Many2one('test_complete_field.sub_model')
    compute_m2o_field = fields.Many2one(
        'test_complete_field.sub_model', compute="_compute_m2o_field",
        search="_search_m2o_compute_field"
    )

    def _compute_m2o_field(self):
        for record in self:
            if record.boolean_field:
                record.compute_m2o_field = record.m2o_field

    @api.model
    def _search_m2o_compute_field(self, operator, operand):
        return [('m2o_field', operator, operand)]


class SubModel(models.Model):
    _name = 'test_complete_field.sub_model'
    _description = 'Sub Model'

    name = fields.Char()
    tag = fields.Integer()

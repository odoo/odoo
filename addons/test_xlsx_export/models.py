# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class NewModel(models.Model):
    _name = 'export.integer'
    _description = 'Export: Integer'

    value = fields.Integer(default=4)

    def name_get(self):
        return [(record.id, "%s:%s" % (self._name, record.value)) for record in self]

class GroupOperator(models.Model):
    _name = 'export.group_operator'
    _description = 'Export Group Operator'

    int_sum = fields.Integer(group_operator='sum')
    int_max = fields.Integer(group_operator='max')
    float_min = fields.Float(group_operator='min')
    float_avg = fields.Float(group_operator='avg')
    float_monetary = fields.Monetary(currency_field='currency_id', group_operator='sum')
    currency_id = fields.Many2one('res.currency')
    date_max = fields.Date(group_operator='max')
    bool_and = fields.Boolean(group_operator='bool_and')
    bool_or = fields.Boolean(group_operator='bool_or')
    many2one = fields.Many2one('export.integer')
    one2many = fields.One2many('export.group_operator.one2many', 'parent_id')

class GroupOperatorO2M(models.Model):
    _name = 'export.group_operator.one2many'
    _description = 'Export Group Operator One2Many'

    parent_id = fields.Many2one('export.group_operator')
    value = fields.Integer()

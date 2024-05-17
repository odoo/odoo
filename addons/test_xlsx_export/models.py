# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class NewModel(models.Model):
    _name = 'export.integer'
    _description = 'Export: Integer'

    value = fields.Integer(default=4)

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{self._name}:{record.value}"


class ExportAggregator(models.Model):
    _name = 'export.aggregator'
    _description = 'Export Aggregator'

    int_sum = fields.Integer(aggregator='sum')
    int_max = fields.Integer(aggregator='max')
    float_min = fields.Float(aggregator='min')
    float_avg = fields.Float(aggregator='avg')
    float_monetary = fields.Monetary(currency_field='currency_id', aggregator='sum')
    currency_id = fields.Many2one('res.currency')
    date_max = fields.Date(aggregator='max')
    bool_and = fields.Boolean(aggregator='bool_and')
    bool_or = fields.Boolean(aggregator='bool_or')
    many2one = fields.Many2one('export.integer')
    one2many = fields.One2many('export.aggregator.one2many', 'parent_id')
    active = fields.Boolean(default=True)


class ExportAggregatorO2M(models.Model):
    _name = 'export.aggregator.one2many'
    _description = 'Export Aggregator One2Many'

    parent_id = fields.Many2one('export.aggregator')
    value = fields.Integer()

# -*- coding: utf-8 -*-

from odoo import models, fields, api


class custom_report(models.Model):
    _name = 'custom.report'
    _description = 'custom.report'

    name = fields.Char()
    value = fields.Integer()
    value2 = fields.Float(compute="_value_pc", store=True)
    description = fields.Text()
    rex_id = fields.One2many('custom.rex.report', 'custom_id', string='Rex')
    @api.depends('value')
    def _value_pc(self):
        for record in self:
            record.value2 = float(record.value) / 100



class custom_rex_report(models.Model):
    _name = 'custom.rex.report'
    _description = 'custom.rex.report'
    sex = fields.Char('性别')
    age = fields.Char('年龄')
    description2 = fields.Text('描述2')
    custom_id = fields.Many2one('custom.report','Custom Report')
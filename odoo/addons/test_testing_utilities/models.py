# -*- coding: utf-8 -*-
from __future__ import division
from odoo import api, fields, models

class A(models.Model):
    _name = 'test_testing_utilities.a'

    f1 = fields.Integer(required=True)
    f2 = fields.Integer(default=42)
    f3 = fields.Integer()
    f4 = fields.Integer(compute='_compute_f4')

    @api.onchange('f2')
    def _on_change_f2(self):
        self.f3 = int(self.f2 / 2)

    @api.depends('f1', 'f2')
    def _compute_f4(self):
        for r in self:
            r.f4 = r.f2 / (r.f1 or 1)

class B(models.Model):
    _name = 'test_testing_utilities.readonly'

    f1 = fields.Integer(default=1, readonly=True)
    f2 = fields.Integer(compute='_compute_f2')

    @api.depends('f1')
    def _compute_f2(self):
        for r in self:
            r.f2 = 2 * r.f1

class C(models.Model):
    _name = 'test_testing_utilities.c'

    name = fields.Char("name", required=True)
    f2 = fields.Many2one('test_testing_utilities.m2o')

    @api.onchange('f2')
    def _on_change_f2(self):
        self.name = self.f2.name

class M2O(models.Model):
    _name = 'test_testing_utilities.m2o'

    name = fields.Char(required=True)

class M2Onchange(models.Model):
    _name = 'test_testing_utilities.d'

    # used to check that defaults & onchange to m2o work
    f = fields.Many2one(
        'test_testing_utilities.m2o',
        required=True,
        default=lambda self: self.env['test_testing_utilities.m2o'].search(
            [], limit=1
        )
    )
    f2 = fields.Char()

    @api.onchange('f2')
    def _on_change_f2(self):
        self.f = self.env['test_testing_utilities.m2o'].search([
            ('name', 'ilike', self.f2),
        ], limit=1)

class M2MChange(models.Model):
    _name = 'test_testing_utilities.e'

    m2m = fields.Many2many('test_testing_utilities.sub2')
    count = fields.Integer(compute='_m2m_count')

    @api.depends('m2m')
    def _m2m_count(self):
        for r in self:
            r.count = len(r.m2m)

class M2MSub(models.Model):
    _name = 'test_testing_utilities.sub2'

    name = fields.Char()

class M2MChange2(models.Model):
    _name = 'test_testing_utilities.f'

    def _get_some(self):
        r = self.env['test_testing_utilities.sub2'].search([], limit=2)
        return r

    m2m = fields.Many2many(
        'test_testing_utilities.sub2',
        default=_get_some,
    )
    m2o = fields.Many2one('test_testing_utilities.sub2')

    @api.onchange('m2o')
    def _on_change_m2o(self):
        self.m2m = self.m2m | self.m2o

class M2MReadonly(models.Model):
    _name = 'test_testing_utilities.g'

    m2m = fields.Many2many('test_testing_utilities.sub3', readonly=True)

class M2MSub3(models.Model):
    _name = 'test_testing_utilities.sub3'

    name = fields.Char()

class O2MChange(models.Model):
    _name = 'test_testing_utilities.parent'

    value = fields.Integer(default=1)
    v = fields.Integer()
    subs = fields.One2many('test_testing_utilities.sub', 'parent_id')

    @api.onchange('value', 'subs')
    def _onchange_values(self):
        self.v = self.value + sum(s.value for s in self.subs)

class O2MSub(models.Model):
    _name = 'test_testing_utilities.sub'

    name = fields.Char(compute='_compute_name')
    value = fields.Integer(default=2)
    v = fields.Integer()
    parent_id = fields.Many2one('test_testing_utilities.parent')
    has_parent = fields.Boolean()

    @api.onchange('value')
    def _onchange_value(self):
        self.v = self.value

    @api.depends('v')
    def _compute_name(self):
        for r in self:
            r.name = str(r.v)

    @api.onchange('has_parent')
    def _onchange_has_parent(self):
        self.has_parent = bool(self.parent_id)
        if self.has_parent:
            self.value = self.parent_id.value

class O2MDefault(models.Model):
    _name = 'test_testing_utilities.default'

    def _default_subs(self):
        return [
            (0, 0, {'v': 5})
        ]
    value = fields.Integer(default=1)
    v = fields.Integer()
    subs = fields.One2many('test_testing_utilities.sub3', 'parent_id', default=_default_subs)

class O2MSub3(models.Model):
    _name = 'test_testing_utilities.sub3'

    name = fields.Char(compute='_compute_name')
    value = fields.Integer(default=2)
    v = fields.Integer(default=6)
    parent_id = fields.Many2one('test_testing_utilities.default')

    @api.onchange('value')
    def _onchange_value(self):
        self.v = self.value

    @api.depends('v')
    def _compute_name(self):
        for r in self:
            r.name = str(r.v)

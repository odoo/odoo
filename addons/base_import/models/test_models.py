# -*- coding: utf-8 -*-
from odoo import fields, models


def name(suffix_name):
    return 'base_import.tests.models.%s' % suffix_name


class Char(models.Model):
    _name = name('char')
    _description = 'Tests : Base Import Model, Character'

    value = fields.Char()
class CharRequired(models.Model):
    _name = name('char.required')
    _description = 'Tests : Base Import Model, Character required'

    value = fields.Char(required=True)

class CharReadonly(models.Model):
    _name = name('char.readonly')
    _description = 'Tests : Base Import Model, Character readonly'

    value = fields.Char(readonly=True)

class CharStates(models.Model):
    _name = name('char.states')
    _description = 'Tests : Base Import Model, Character states'

    value = fields.Char(readonly=True, states={'draft': [('readonly', False)]})

class CharNoreadonly(models.Model):
    _name = name('char.noreadonly')
    _description = 'Tests : Base Import Model, Character No readonly'

    value = fields.Char(readonly=True, states={'draft': [('invisible', True)]})

class CharStillreadonly(models.Model):
    _name = name('char.stillreadonly')
    _description = 'Tests : Base Import Model, Character still readonly'

    value = fields.Char(readonly=True, states={'draft': [('readonly', True)]})

# TODO: complex field (m2m, o2m, m2o)
class M2o(models.Model):
    _name = name('m2o')
    _description = 'Tests : Base Import Model, Many to One'

    value = fields.Many2one(name('m2o.related'))

class M2oRelated(models.Model):
    _name = name('m2o.related')
    _description = 'Tests : Base Import Model, Many to One related'

    value = fields.Integer(default=42)

class M2oRequired(models.Model):
    _name = name('m2o.required')
    _description = 'Tests : Base Import Model, Many to One required'

    value = fields.Many2one(name('m2o.required.related'), required=True)

class M2oRequiredRelated(models.Model):
    _name = name('m2o.required.related')
    _description = 'Tests : Base Import Model, Many to One required related'

    value = fields.Integer(default=42)

class O2m(models.Model):
    _name = name('o2m')
    _description = 'Tests : Base Import Model, One to Many'

    value = fields.One2many(name('o2m.child'), 'parent_id')

class O2mChild(models.Model):
    _name = name('o2m.child')
    _description = 'Tests : Base Import Model, One to Many child'

    parent_id = fields.Many2one(name('o2m'))
    value = fields.Integer()

class PreviewModel(models.Model):
    _name = name('preview')
    _description = 'Tests : Base Import Model Preview'

    name = fields.Char('Name')
    somevalue = fields.Integer(string='Some Value', required=True)
    othervalue = fields.Integer(string='Other Variable')

class FloatModel(models.Model):
    _name = name('float')
    _description = 'Tests: Base Import Model Float'

    value = fields.Float()
    value2 = fields.Monetary()
    currency_id = fields.Many2one('res.currency')

class ComplexModel(models.Model):
    _name = name('complex')
    _description = 'Tests: Base Import Model Complex'

    f = fields.Float()
    m = fields.Monetary()
    c = fields.Char()
    currency_id = fields.Many2one('res.currency')
    d = fields.Date()
    dt = fields.Datetime()

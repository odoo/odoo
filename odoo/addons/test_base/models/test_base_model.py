# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models

class TestOne2many(models.Model):
    _name = 'test_o2m_relational.model'
    _description = 'test relation model o2m'

    name = fields.Char()
    model_id = fields.Many2one('test_base.model')
    code = fields.Char()

class TestMany2oneLevel1(models.Model):
    _name = 'test_m2o_level_1.model'
    _description = 'test model level 1'

    name = fields.Char()

class TestMany2one(models.Model):
    _name = 'test_m2o_relational.model'
    _description = 'test relation model m2o'

    name = fields.Char()
    many2one_id = fields.Many2one('test_m2o_relational.model')
    many2one_level_id = fields.Many2one('test_m2o_level_1.model')
    base_model_id = fields.Many2one('test_base.model')
    code = fields.Char()

class TestMany2many(models.Model):
    _name = 'test_m2m_relational.model'
    _description = 'test relation model m2m'

    name = fields.Char()
    parent_id = fields.Many2one('test_m2m_relational.model')

class TestModel(models.Model):
    _name = "test_base.model"
    _description = 'test mail model'

    name = fields.Char()
    sequence = fields.Integer()
    many2one_id = fields.Many2one('test_m2o_relational.model')
    parent_id = fields.Many2one('test_base.model', 'many2one_id')
    translate_id = fields.Many2one('test_translation.model')
    one2many_ids = fields.One2many('test_o2m_relational.model', 'model_id')
    child_ids = fields.One2many('test_base.model', 'parent_id')
    many2many_ids = fields.Many2many('test_m2m_relational.model', 'base_relational_rel', 'model_id', 'rel_id')
    is_boolean = fields.Boolean(default=True)
    date = fields.Date()
    email = fields.Char()
    active = fields.Boolean(default=True)
    ref = fields.Char()
    image = fields.Binary(attachment=True)

class TestM2oRequired(models.Model):
    _name = 'test_required_relational.model'
    _description = 'test required relation model'

    name = fields.Char()

class TestRequiredTest(models.Model):
    _name = "test_required.model"
    _description = 'test required model'

    name = fields.Char()
    m2o_required_id = fields.Many2one('test_required_relational.model', required=True, help="Many2one required field")

class TestTranslate(models.Model):
    _name = 'test_translation.model'
    _description = 'test translation model'

    name = fields.Char(translate=True)

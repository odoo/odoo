# -*- coding: utf-8 -*-
from odoo import fields, models
from odoo.tools.translate import html_translate


class TestTranslationRelatedModel1(models.Model):
    _name = 'test.translation.related.model1'
    _description = 'Translation Test 1'

    name = fields.Char('Name', translate=True)
    html = fields.Html('HTML', translate=html_translate)

class TestTranslationRelatedModel2(models.Model):
    _name = 'test.translation.related.model2'
    _description = 'Translation Test 2'

    parent_id = fields.Many2one('test.translation.related.model1', string='Parent Model')
    name = fields.Char('Name Related', related='parent_id.name', readonly=False)
    html = fields.Html('HTML Related', related='parent_id.html', readonly=False)

class TestTranslationRelatedModel3(models.Model):
    _name = 'test.translation.related.model3'
    _description = 'Translation Test 3'

    parent_id = fields.Many2one('test.translation.related.model2', string='Parent Model')
    name = fields.Char('Name Related', related='parent_id.name', readonly=False)
    html = fields.Html('HTML Related', related='parent_id.html', readonly=False)

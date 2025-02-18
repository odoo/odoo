# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class Test_ConverterTest_Model(models.Model):
    _name = 'test_converter.test_model'
    _description = 'Test Converter Model'

    char = fields.Char()
    integer = fields.Integer()
    float = fields.Float()
    numeric = fields.Float(digits=(16, 2))
    many2one = fields.Many2one('test_converter.test_model.sub')
    binary = fields.Binary(attachment=False)
    date = fields.Date()
    datetime = fields.Datetime()
    selection_str = fields.Selection([
        ('A', u"Qu'il n'est pas arrivé à Toronto"),
        ('B', u"Qu'il était supposé arriver à Toronto"),
        ('C', u"Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?"),
        ('D', u"La réponse D"),
    ], string=u"Lorsqu'un pancake prend l'avion à destination de Toronto et "
              u"qu'il fait une escale technique à St Claude, on dit:")
    html = fields.Html()
    text = fields.Text()


class Test_ConverterTest_ModelSub(models.Model):
    _name = 'test_converter.test_model.sub'
    _description = 'Subtraction For Test Model & Test Converter'
    name = fields.Char()


class Test_ConverterMonetary(models.Model):
    _name = 'test_converter.monetary'
    _description = 'Test Converter Monetary'
    value = fields.Float(digits=(16, 55))

# -*- coding: utf-8 -*-
from openerp import models, fields

class TestConverter(models.Model):
    _name = 'website.converter.test'

    # disable translation export for those brilliant field labels and values
    _translate = False

    char = fields.Char()
    integer = fields.Integer()
    float = fields.Float()
    numeric = fields.Float(digits=(16, 2))
    many2one = fields.Many2one('website.converter.test.sub')
    binary = fields.Binary()
    date = fields.Date()
    datetime = fields.Datetime()
    selection = fields.Selection([
        (1, "réponse A"),
        (2, "réponse B"),
        (3, "réponse C"),
        (4, "réponse D"),
    ])
    selection_str = fields.Selection([
        ('A', "Qu'il n'est pas arrivé à Toronto"),
        ('B', "Qu'il était supposé arriver à Toronto"),
        ('C', "Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?"),
        ('D', "La réponse D"),
    ], string=u"Lorsqu'un pancake prend l'avion à destination de Toronto et "
              u"qu'il fait une escale technique à St Claude, on dit:")
    html = fields.Html()
    text = fields.Text()


class TestConverterSub(models.Model):
    _name = 'website.converter.test.sub'

    name = fields.Char()

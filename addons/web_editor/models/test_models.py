# -*- coding: utf-8 -*-
from openerp.osv import orm, fields


class test_converter(orm.Model):
    _name = 'web_editor.converter.test'

    # disable translation export for those brilliant field labels and values
    _translate = False

    _columns = {
        'char': fields.char(),
        'integer': fields.integer(),
        'float': fields.float(),
        'numeric': fields.float(digits=(16, 2)),
        'many2one': fields.many2one('web_editor.converter.test.sub'),
        'binary': fields.binary(),
        'date': fields.date(),
        'datetime': fields.datetime(),
        'selection': fields.selection([
            (1, "réponse A"),
            (2, "réponse B"),
            (3, "réponse C"),
            (4, "réponse D"),
        ]),
        'selection_str': fields.selection([
            ('A', "Qu'il n'est pas arrivé à Toronto"),
            ('B', "Qu'il était supposé arriver à Toronto"),
            ('C', "Qu'est-ce qu'il fout ce maudit pancake, tabernacle ?"),
            ('D', "La réponse D"),
        ], string=u"Lorsqu'un pancake prend l'avion à destination de Toronto et "
                  u"qu'il fait une escale technique à St Claude, on dit:"),
        'html': fields.html(),
        'text': fields.text(),
    }


class test_converter_sub(orm.Model):
    _name = 'web_editor.converter.test.sub'

    _columns = {
        'name': fields.char(),
    }

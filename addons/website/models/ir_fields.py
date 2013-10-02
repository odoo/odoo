# -*- coding: utf-8 -*-
from lxml import etree, html

from openerp.osv import orm, fields
from openerp.tools import ustr

class converter(orm.Model):
    _inherit = 'ir.fields.converter'

    def _html_to_integer(self, cr, uid, model, column, value, context=None):
        return int(value.text_content().strip()), []

    def _html_to_float(self, cr, uid, model, column, value, context=None):
        return float(value.text_content().strip()), []

    def _html_to_passthrough(self, cr, uid, model, column, value, context=None):
        return value.text_content().strip(), []

    _html_to_char = _html_to_date = _html_to_datetime = _html_to_passthrough

    def _html_to_text(self, cr, uid, model, column, value, context=None):
        return value.text_content(), []

    def _html_to_selection(self, cr, uid, model, column, value, context=None):
        text = value.text_content().strip()

        selection = column.reify(cr, uid, model, column, context=context)
        for k, v in selection:
            if isinstance(v, str):
                v = ustr(v)
            if text == v:
                return k, []

        warning = u"No value found for label %s in selection %s" % (text, selection)
        # FIXME: ?
        return False, [Warning(warning.encode('utf-8'))]

    def _html_to_many2one(self, cr, uid, model, column, value, context=None):
        matches = self.pool[column._obj].name_search(
            cr, uid, name=value.text_content().strip(), context=context)
        # FIXME: more than one match, error reporting
        return matches[0][0], []

    def _html_to_html(self, cr, uid, model, column, value, context=None):
        content = []
        if value.text: content.append(value.text)
        content.extend(html.tostring(child)
                       for child in value.iterchildren(tag=etree.Element))
        return '\n'.join(content), []


class test_converter(orm.Model):
    _name = 'website.converter.test'

    _columns = {
        'char': fields.char(),
        'integer': fields.integer(),
        'float': fields.float(),
        'numeric': fields.float(digits=(16, 2)),
        'many2one': fields.many2one('website.converter.test.sub'),
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
        ], string="Lorsqu'un pancake prend l'avion à destination de Toronto et "
                  "qu'il fait une escale technique à St Claude, on dit:"),
        'html': fields.html(),
        'text': fields.text(),
    }


class test_converter_sub(orm.Model):
    _name = 'website.converter.test.sub'

    _columns = {
        'name': fields.char(),
    }

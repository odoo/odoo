# -*- coding: utf-8 -*-
"""
Website-context rendering needs to add some metadata to rendered fields,
as well as render a few fields differently.

Also, adds methods to convert values back to openerp models.
"""

import itertools

import werkzeug.utils
from lxml import etree, html

from openerp.osv import orm, fields
from openerp.tools import ustr

class QWeb(orm.AbstractModel):
    """ QWeb object for rendering stuff in the website context
    """
    _name = 'website.qweb'
    _inherit = 'ir.qweb'

    def get_converter_for(self, field_type):
        return self.pool.get(
            'website.qweb.field.' + field_type,
            self.pool['website.qweb.field'])

class Field(orm.AbstractModel):
    _name = 'website.qweb.field'
    _inherit = 'ir.qweb.field'

    def attributes(self, cr, uid, field_name, record, options,
                   source_element, g_att, t_att, qweb_context):
        column = record._model._all_columns[field_name].column
        return itertools.chain(
            super(Field, self).attributes(cr, uid, field_name, record, options,
                                          source_element, g_att, t_att,
                                          qweb_context),
            [('data-oe-translate', 1 if column.translate else 0)]
        )

    def value_from_string(self, value):
        return value

    def from_html(self, cr, uid, model, column, element, context=None):
        return self.value_from_string(element.text_content().strip())

class Integer(orm.AbstractModel):
    _name = 'website.qweb.field.integer'
    _inherit = ['website.qweb.field']

    value_from_string = int

class Float(orm.AbstractModel):
    _name = 'website.qweb.field.float'
    _inherit = ['website.qweb.field', 'ir.qweb.field.float']

    value_from_string = float

class Text(orm.AbstractModel):
    _name = 'website.qweb.field.text'
    _inherit = ['website.qweb.field', 'ir.qweb.field.text']

    def from_html(self, cr, uid, model, column, element, context=None):
        return element.text_content()

class Selection(orm.AbstractModel):
    _name = 'website.qweb.field.selection'
    _inherit = ['website.qweb.field', 'ir.qweb.field.selection']

    def from_html(self, cr, uid, model, column, element, context=None):
        value = element.text_content().strip()
        selection = column.reify(cr, uid, model, column, context=context)
        for k, v in selection:
            if isinstance(v, str):
                v = ustr(v)
            if value == v:
                return k

        raise ValueError(u"No value found for label %s in selection %s" % (
                         value, selection))

class ManyToOne(orm.AbstractModel):
    _name = 'website.qweb.field.many2one'
    _inherit = ['website.qweb.field', 'ir.qweb.field.many2one']

    def from_html(self, cr, uid, model, column, element, context=None):
        # FIXME: this behavior is really weird, what if the user wanted to edit the name of the related thingy? Should m2os really be editable without a widget?
        matches = self.pool[column._obj].name_search(
            cr, uid, name=element.text_content().strip(), context=context)
        # FIXME: no match? More than 1 match?
        assert len(matches) == 1
        return matches[0][0]

class HTML(orm.AbstractModel):
    _name = 'website.qweb.field.html'
    _inherit = ['website.qweb.field', 'ir.qweb.field.html']

    def from_html(self, cr, uid, model, column, element, context=None):
        content = []
        if element.text: content.append(element.text)
        content.extend(html.tostring(child)
                       for child in element.iterchildren(tag=etree.Element))
        return '\n'.join(content)


class Image(orm.AbstractModel):
    """
    Widget options:

    ``class``
        set as attribute on the generated <img> tag
    """
    _name = 'website.qweb.field.image'
    _inherit = ['website.qweb.field', 'ir.qweb.field.image']

    def to_html(self, cr, uid, field_name, record, options,
                source_element, t_att, g_att, qweb_context):
        assert source_element.nodeName != 'img',\
            "Oddly enough, the root tag of an image field can not be img. " \
            "That is because the image goes into the tag, or it gets the " \
            "hose again."

        return super(Image, self).to_html(
            cr, uid, field_name, record, options,
            source_element, t_att, g_att, qweb_context)

    def record_to_html(self, cr, uid, field_name, record, column, options=None):
        cls = ''
        if 'class' in options:
            cls = ' class="%s"' % werkzeug.utils.escape(options['class'])

        return '<img%s src="/website/image?model=%s&field=%s&id=%s"/>' % (
            cls, record._model._name, field_name, record.id)

class Monetary(orm.AbstractModel):
    _name = 'website.qweb.field.monetary'
    _inherit = ['website.qweb.field', 'ir.qweb.field.monetary']

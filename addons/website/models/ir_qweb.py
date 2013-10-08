# -*- coding: utf-8 -*-
"""
Website-context rendering needs to add some metadata to rendered fields,
as well as render a few fields differently.

Also, adds methods to convert values back to openerp models.
"""

import itertools

import werkzeug.utils

from openerp.osv import orm, fields

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

class Float(orm.AbstractModel):
    _name = 'website.qweb.field.float'
    _inherit = ['website.qweb.field', 'ir.qweb.field.float']

class Text(orm.AbstractModel):
    _name = 'website.qweb.field.text'
    _inherit = ['website.qweb.field', 'ir.qweb.field.text']

class Selection(orm.AbstractModel):
    _name = 'website.qweb.field.selection'
    _inherit = ['website.qweb.field', 'ir.qweb.field.selection']

class ManyToOne(orm.AbstractModel):
    _name = 'website.qweb.field.many2one'
    _inherit = ['website.qweb.field', 'ir.qweb.field.many2one']

class HTML(orm.AbstractModel):
    _name = 'website.qweb.field.html'
    _inherit = ['website.qweb.field', 'ir.qweb.field.html']

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

class Currency(orm.AbstractModel):
    _name = 'website.qweb.field.currency'
    _inherit = ['website.qweb.field', 'ir.qweb.field.currency']

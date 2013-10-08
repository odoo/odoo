# -*- coding: utf-8 -*-
import itertools

from openerp.osv import orm, fields

class QWeb(orm.AbstractModel):
    """ QWeb object for rendering stuff in the website context

    Website-context rendering needs to add some metadata to rendered fields,
    as well as render a few fields differently.

    Also, add methods to convert values back to openerp models.
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
    _name = 'website.qweb.field.image'
    _inherit = ['website.qweb.field', 'ir.qweb.field.image']

class Currency(orm.AbstractModel):
    _name = 'website.qweb.field.currency'
    _inherit = ['website.qweb.field', 'ir.qweb.field.currency']

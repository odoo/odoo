# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from openerp import models, api
from openerp.tools.translate import encode, xml_translate

def edit_translation_mapping(data):
    data = dict(data, model=data['name'].partition(',')[0])
    return '<span data-oe-model="%(model)s" data-oe-translation-id="%(id)s" data-oe-translation-state="%(state)s">%(value)s</span>' % data

class ir_translation(models.Model):
    _inherit = 'ir.translation'

    @api.model
    def _get_terms_mapping(self, field, records):
        if self._context.get('edit_translations'):
            self.insert_missing(field, records)
            return edit_translation_mapping
        return super(ir_translation, self)._get_terms_mapping(field, records)

    @api.multi
    def save_html(self, value):
        """ Convert the HTML fragment ``value`` to XML if necessary, and write
        it as the value of translation ``self``.
        """
        assert len(self) == 1 and self.type == 'model'
        mname, fname = self.name.split(',')
        field = self.env[mname]._fields[fname]
        if field.translate == xml_translate:
            # wrap value inside a div and parse it as HTML
            div = "<div>%s</div>" % encode(value)
            root = etree.fromstring(div, etree.HTMLParser(encoding='utf-8'))
            # root is html > body > div
            # serialize div as XML and discard surrounding tags
            value = etree.tostring(root[0][0], encoding='utf-8')[5:-6]
        return self.write({'value': value})

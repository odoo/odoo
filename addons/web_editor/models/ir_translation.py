# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree, html

from odoo import models, api
from odoo.tools.translate import encode, xml_translate, html_translate


def edit_translation_mapping(data):
    value = data['value'] or data['src']
    element = html.fragment_fromstring(value, create_parent="div")
    for el in element.getiterator():
        if el.tag == 't' and 't-out' in el.attrib:
            escape_el = etree.Element("t-translate-wrap")
            el.getparent().replace(el, escape_el)
            escape_el.set('data-oe-original-expression', el.attrib['t-out'])
            escape_el.tail = el.tail
            el.tail = ''
            escape_el.append(el)
        elif 't-out' in el.attrib:
            el.set('data-oe-original-expression', el.attrib['t-out'])

    value = html.tostring(element, encoding="unicode")
    # Remove the parent div
    value = value[5:-6]

    data = dict(data, model=data['name'].partition(',')[0], value=value)

    return '<span data-oe-model="%(model)s" data-oe-translation-id="%(id)s" data-oe-translation-state="%(state)s">%(value)s</span>' % data

def get_xml_node_from_translation(value):
    # wrap value inside a div and parse it as HTML
    div = "<div>%s</div>" % encode(value)
    root = etree.fromstring(div, etree.HTMLParser(encoding='utf-8'))

    for el in root.getiterator():
        if el.tag == 't-translate-wrap':
            t_el = etree.Element("t")
            t_el.set('t-out', el.attrib['data-oe-original-expression'])
            t_el.tail = el.tail
            el.getparent().replace(el, t_el)
        elif 'data-oe-original-expression' in el.attrib:
            el.set('t-out', el.attrib['data-oe-original-expression'])
            del el.attrib['data-oe-original-expression']
    return root

class IrTranslation(models.Model):
    _inherit = 'ir.translation'

    @api.model
    def _get_terms_mapping(self, field, records):
        if self._context.get('edit_translations'):
            self.insert_missing(field, records)
            return edit_translation_mapping
        return super(IrTranslation, self)._get_terms_mapping(field, records)

    def save_html(self, value):
        """ Convert the HTML fragment ``value`` to XML if necessary, and write
        it as the value of translation ``self``.
        """
        assert len(self) == 1 and self.type == 'model_terms'
        mname, fname = self.name.split(',')
        field = self.env[mname]._fields[fname]
        if field.translate == xml_translate:
            root = get_xml_node_from_translation(value)
            # root is html > body > div
            # serialize div as XML and discard surrounding tags
            value = etree.tostring(root[0][0], encoding='utf-8')[5:-6]
        elif field.translate == html_translate:
            root = get_xml_node_from_translation(value)
            # root is html > body > div
            # serialize div as HTML and discard surrounding tags
            value = etree.tostring(root[0][0], encoding='utf-8', method='html')[5:-6]
        return self.write({'value': value})

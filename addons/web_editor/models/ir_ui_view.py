# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
from lxml import etree, html

from odoo.exceptions import AccessError
from odoo import api, models


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.multi
    def render(self, values=None, engine='ir.qweb'):
        if values and values.get('editable'):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                values['editable'] = False

        return super(IrUiView, self).render(values=values, engine=engine)

    #------------------------------------------------------
    # Save from html
    #------------------------------------------------------

    @api.model
    def extract_embedded_fields(self, arch):
        return arch.xpath('//*[@data-oe-model != "ir.ui.view"]')

    @api.model
    def save_embedded_field(self, el):
        Model = self.env[el.get('data-oe-model')]
        field = el.get('data-oe-field')

        model = 'ir.qweb.field.' + el.get('data-oe-type')
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']
        value = converter.from_html(Model, Model._fields[field], el)

        if value is not None:
            # TODO: batch writes?
            Model.browse(int(el.get('data-oe-id'))).write({field: value})

    def _pretty_arch(self, arch):
        # remove_blank_string does not seem to work on HTMLParser, and
        # pretty-printing with lxml more or less requires stripping
        # whitespace: http://lxml.de/FAQ.html#why-doesn-t-the-pretty-print-option-reformat-my-xml-output
        # so serialize to XML, parse as XML (remove whitespace) then serialize
        # as XML (pretty print)
        arch_no_whitespace = etree.fromstring(
            etree.tostring(arch, encoding='utf-8'),
            parser=etree.XMLParser(encoding='utf-8', remove_blank_text=True))
        return etree.tostring(
            arch_no_whitespace, encoding='unicode', pretty_print=True)

    @api.multi
    def replace_arch_section(self, section_xpath, replacement):
        # the root of the arch section shouldn't actually be replaced as it's
        # not really editable itself, only the content truly is editable.
        self.ensure_one()
        arch = etree.fromstring(self.arch.encode('utf-8'))
        # => get the replacement root
        if not section_xpath:
            root = arch
        else:
            # ensure there's only one match
            [root] = arch.xpath(section_xpath)

        root.text = replacement.text
        root.tail = replacement.tail
        # replace all children
        del root[:]
        for child in replacement:
            root.append(copy.deepcopy(child))

        return arch

    @api.model
    def to_field_ref(self, el):
        # filter out meta-information inserted in the document
        attributes = dict((k, v) for k, v in el.items()
                          if not k.startswith('data-oe-'))
        attributes['t-field'] = el.get('data-oe-expression')

        out = html.html_parser.makeelement(el.tag, attrib=attributes)
        out.tail = el.tail
        return out

    @api.multi
    def save(self, value, xpath=None):
        """ Update a view section. The view section may embed fields to write

        :param str xpath: valid xpath to the tag to replace
        """
        arch_section = html.fromstring(
            value, parser=html.HTMLParser(encoding='utf-8'))

        if xpath is None:
            # value is an embedded field on its own, not a view section
            self.save_embedded_field(arch_section)
            return

        for el in self.extract_embedded_fields(arch_section):
            self.save_embedded_field(el)

            # transform embedded field back to t-field
            el.getparent().replace(el, self.to_field_ref(el))

        for view in self:
            arch = view.replace_arch_section(xpath, arch_section)
            view.write({'arch': view._pretty_arch(arch)})

        self.sudo().mapped('model_data_id').write({'noupdate': True})

# -*- coding: utf-8 -*-
import copy
import openerp
from openerp.exceptions import AccessError
from openerp.osv import osv
from lxml import etree, html
from openerp import api


class view(osv.osv):
    _inherit = 'ir.ui.view'

    @api.cr_uid_ids_context
    def render(self, cr, uid, id_or_xml_id, values=None, engine='ir.qweb', context=None):
        if not values:
            values = {}
        if values.get('editable'):
            try:
                if not isinstance(id_or_xml_id, (int, long)):
                    if '.' not in id_or_xml_id:
                        raise ValueError('Invalid template id: %r' % (id_or_xml_id,))
                    id_or_xml_id = self.get_view_id(cr, uid, id_or_xml_id, context=context)

                self.check_access_rule(cr, uid, [id_or_xml_id], 'write', context=context)

            except AccessError:
                values['editable'] = False

        return super(view, self).render(cr, uid, id_or_xml_id, values=values, engine=engine, context=context)

    #------------------------------------------------------
    # Save from html
    #------------------------------------------------------

    def extract_embedded_fields(self, cr, uid, arch, context=None):
        return arch.xpath('//*[@data-oe-model != "ir.ui.view"]')

    def save_embedded_field(self, cr, uid, el, context=None):
        Model = self.pool[el.get('data-oe-model')]
        field = el.get('data-oe-field')

        converter = self.pool['ir.qweb'].get_converter_for(el.get('data-oe-type'))
        value = converter.from_html(cr, uid, Model, Model._fields[field], el)

        if value is not None:
            # TODO: batch writes?
            Model.write(cr, uid, [int(el.get('data-oe-id'))], {
                field: value
            }, context=context)

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

    def replace_arch_section(self, cr, uid, view_id, section_xpath, replacement, context=None):
        # the root of the arch section shouldn't actually be replaced as it's
        # not really editable itself, only the content truly is editable.

        [view] = self.browse(cr, uid, [view_id], context=context)
        arch = etree.fromstring(view.arch.encode('utf-8'))
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

    def to_field_ref(self, cr, uid, el, context=None):
        # filter out meta-information inserted in the document
        attributes = dict((k, v) for k, v in el.items()
                          if not k.startswith('data-oe-'))
        attributes['t-field'] = el.get('data-oe-expression')

        out = html.html_parser.makeelement(el.tag, attrib=attributes)
        out.tail = el.tail
        return out

    def save(self, cr, uid, res_id, value, xpath=None, context=None):
        """ Update a view section. The view section may embed fields to write

        :param str model:
        :param int res_id:
        :param str xpath: valid xpath to the tag to replace
        """
        res_id = int(res_id)

        arch_section = html.fromstring(
            value, parser=html.HTMLParser(encoding='utf-8'))

        if xpath is None:
            # value is an embedded field on its own, not a view section
            self.save_embedded_field(cr, uid, arch_section, context=context)
            return

        for el in self.extract_embedded_fields(cr, uid, arch_section, context=context):
            self.save_embedded_field(cr, uid, el, context=context)

            # transform embedded field back to t-field
            el.getparent().replace(el, self.to_field_ref(cr, uid, el, context=context))

        arch = self.replace_arch_section(cr, uid, res_id, xpath, arch_section, context=context)
        self.write(cr, uid, res_id, {
            'arch': self._pretty_arch(arch)
        }, context=context)

        view = self.browse(cr, openerp.SUPERUSER_ID, res_id, context=context)
        if view.model_data_id:
            view.model_data_id.write({'noupdate': True})

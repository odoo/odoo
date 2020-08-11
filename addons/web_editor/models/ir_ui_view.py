# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
import logging
from lxml import etree, html

from odoo.exceptions import AccessError
from odoo import api, fields, models
from odoo.tools import pycompat

_logger = logging.getLogger(__name__)

EDITING_ATTRIBUTES = ['data-oe-model', 'data-oe-id', 'data-oe-field', 'data-oe-xpath', 'data-note-id']


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    @api.multi
    def render(self, values=None, engine='ir.qweb', minimal_qcontext=False):
        if values and values.get('editable'):
            try:
                self.check_access_rights('write')
                self.check_access_rule('write')
            except AccessError:
                values['editable'] = False

        return super(IrUiView, self).render(values=values, engine=engine, minimal_qcontext=minimal_qcontext)

    #------------------------------------------------------
    # Save from html
    #------------------------------------------------------

    @api.model
    def extract_embedded_fields(self, arch):
        return arch.xpath('//*[@data-oe-model != "ir.ui.view"]')

    @api.model
    def extract_oe_structures(self, arch):
        return arch.xpath('//*[hasclass("oe_structure")][contains(@id, "oe_structure")]')

    @api.model
    def get_default_lang_code(self):
        return False

    @api.model
    def save_embedded_field(self, el):
        Model = self.env[el.get('data-oe-model')]
        field = el.get('data-oe-field')

        model = 'ir.qweb.field.' + el.get('data-oe-type')
        converter = self.env[model] if model in self.env else self.env['ir.qweb.field']
        value = converter.from_html(Model, Model._fields[field], el)

        if value is not None:
            # TODO: batch writes?
            if not self.env.context.get('lang') and self.get_default_lang_code():
                Model.browse(int(el.get('data-oe-id'))).with_context(lang=self.get_default_lang_code()).write({field: value})
            else:
                Model.browse(int(el.get('data-oe-id'))).write({field: value})

    @api.multi
    def save_oe_structure(self, el):
        self.ensure_one()

        if el.get('id') in self.key:
            # Do not inherit if the oe_structure already has its own inheriting view
            return False

        arch = etree.Element('data')
        xpath = etree.Element('xpath', expr="//*[hasclass('oe_structure')][@id='{}']".format(el.get('id')), position="replace")
        arch.append(xpath)
        attributes = {k: v for k, v in el.attrib.items() if k not in EDITING_ATTRIBUTES}
        structure = etree.Element(el.tag, attrib=attributes)
        structure.text = el.text
        xpath.append(structure)
        for child in el.iterchildren(tag=etree.Element):
            structure.append(copy.deepcopy(child))

        vals = {
            'inherit_id': self.id,
            'name': '%s (%s)' % (self.name, el.get('id')),
            'arch': self._pretty_arch(arch),
            'key': '%s_%s' % (self.key, el.get('id')),
            'type': 'qweb',
            'mode': 'extension',
        }
        vals.update(self._save_oe_structure_hook())
        self.env['ir.ui.view'].create(vals)

        return True

    @api.model
    def _save_oe_structure_hook(self):
        return {}

    @api.model
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

    @api.model
    def _are_archs_equal(self, arch1, arch2):
        # Note that comparing the strings would not be ok as attributes order
        # must not be relevant
        if arch1.tag != arch2.tag:
            return False
        if arch1.text != arch2.text:
            return False
        if arch1.tail != arch2.tail:
            return False
        if arch1.attrib != arch2.attrib:
            return False
        if len(arch1) != len(arch2):
            return False
        return all(self._are_archs_equal(arch1, arch2) for arch1, arch2 in pycompat.izip(arch1, arch2))

    @api.multi
    def replace_arch_section(self, section_xpath, replacement, replace_tail=False):
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
        # Note: after a standard edition, the tail *must not* be replaced
        if replace_tail:
            root.tail = replacement.tail
        # replace all children
        del root[:]
        for child in replacement:
            root.append(copy.deepcopy(child))

        return arch

    @api.model
    def to_field_ref(self, el):
        # filter out meta-information inserted in the document
        attributes = {k: v for k, v in el.attrib.items()
                           if not k.startswith('data-oe-')}
        attributes['t-field'] = el.get('data-oe-expression')

        out = html.html_parser.makeelement(el.tag, attrib=attributes)
        out.tail = el.tail
        return out

    @api.model
    def to_empty_oe_structure(self, el):
        out = html.html_parser.makeelement(el.tag, attrib=el.attrib)
        out.tail = el.tail
        return out

    @api.model
    def _set_noupdate(self):
        self.sudo().mapped('model_data_id').write({'noupdate': True})

    @api.multi
    def save(self, value, xpath=None):
        """ Update a view section. The view section may embed fields to write

        Note that `self` record might not exist when saving an embed field

        :param str xpath: valid xpath to the tag to replace
        """
        self.ensure_one()

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

        for el in self.extract_oe_structures(arch_section):
            if self.save_oe_structure(el):
                # empty oe_structure in parent view
                empty = self.to_empty_oe_structure(el)
                if el == arch_section:
                    arch_section = empty
                else:
                    el.getparent().replace(el, empty)

        new_arch = self.replace_arch_section(xpath, arch_section)
        old_arch = etree.fromstring(self.arch.encode('utf-8'))
        if not self._are_archs_equal(old_arch, new_arch):
            self._set_noupdate()
            self.write({'arch': self._pretty_arch(new_arch)})

    @api.model
    def _view_get_inherited_children(self, view, options):
        return view.inherit_children_ids

    @api.model
    def _view_obj(self, view_id):
        if isinstance(view_id, pycompat.string_types):
            return self.search([('key', '=', view_id)], limit=1) or self.env.ref(view_id)
        elif isinstance(view_id, pycompat.integer_types):
            return self.browse(view_id)
        # It can already be a view object when called by '_views_get()' that is calling '_view_obj'
        # for it's inherit_children_ids, passing them directly as object record.
        return view_id

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates

    @api.model
    def _views_get(self, view_id, options=True, bundles=False, root=True, visited=None):
        """ For a given view ``view_id``, should return:
                * the view itself
                * all views inheriting from it, enabled or not
                  - but not the optional children of a non-enabled child
                * all views called from it (via t-call)
            :returns recordset of ir.ui.view
        """
        try:
            view = self._view_obj(view_id)
        except ValueError:
            _logger.warning("Could not find view object with view_id '%s'", view_id)
            return self.env['ir.ui.view']

        if visited is None:
            visited = []
        while root and view.inherit_id:
            view = view.inherit_id

        views_to_return = view

        node = etree.fromstring(view.arch)
        xpath = "//t[@t-call]"
        if bundles:
            xpath += "| //t[@t-call-assets]"
        for child in node.xpath(xpath):
            try:
                called_view = self._view_obj(child.get('t-call', child.get('t-call-assets')))
            except ValueError:
                continue
            if called_view and called_view not in views_to_return and called_view.id not in visited:
                views_to_return += self._views_get(called_view, options=options, bundles=bundles, visited=visited + views_to_return.ids)

        if not options:
            return views_to_return

        extensions = self._view_get_inherited_children(view, options)

        # Keep options in a deterministic order regardless of their applicability
        for extension in extensions.sorted(key=lambda v: v.id):
            # only return optional grandchildren if this child is enabled
            if extension.id not in visited:
                for ext_view in self._views_get(extension, options=extension.active, root=False, visited=visited + views_to_return.ids):
                    if ext_view not in views_to_return:
                        views_to_return += ext_view
        return views_to_return

    @api.model
    def get_related_views(self, key, bundles=False):
        """ Get inherit view's informations of the template ``key``.
            returns templates info (which can be active or not)
            ``bundles=True`` returns also the asset bundles
        """
        user_groups = set(self.env.user.groups_id)
        View = self.with_context(active_test=False, lang=None)
        views = View._views_get(key, bundles=bundles)
        return views.filtered(lambda v: not v.groups_id or len(user_groups.intersection(v.groups_id)))

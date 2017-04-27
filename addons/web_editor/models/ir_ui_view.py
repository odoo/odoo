# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
import logging
from lxml import etree, html

from odoo.exceptions import AccessError
from odoo import api, models
from odoo.tools import pycompat

_logger = logging.getLogger(__name__)


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

    @api.model
    def _view_obj(self, view_id):
        if isinstance(view_id, basestring):
            return self.env.ref(view_id)
        elif isinstance(view_id, pycompat.integer_types):
            return self.browse(view_id)
        # assume it's already a view object (WTF?)
        return view_id

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates

    @api.model
    def _views_get(self, view_id, options=True, bundles=False, root=True):
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
            return []

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
            if called_view not in views_to_return:
                views_to_return += self._views_get(called_view, options=options, bundles=bundles)

        extensions = view.inherit_children_ids
        if not options:
            # only active children
            extensions = view.inherit_children_ids.filtered(lambda view: view.active)

        # Keep options in a deterministic order regardless of their applicability
        for extension in extensions.sorted(key=lambda v: v.id):
            # only return optional grandchildren if this child is enabled
            for ext_view in self._views_get(extension, options=extension.active, root=False):
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
        views = self.with_context(active_test=False)._views_get(key, bundles=bundles)
        return views.filtered(lambda v: not v.groups_id or len(user_groups.intersection(v.groups_id)))

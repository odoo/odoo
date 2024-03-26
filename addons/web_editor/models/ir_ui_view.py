# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import copy
import logging
import uuid
from lxml import etree, html

from odoo import api, models, _
from odoo.osv import expression
from odoo.exceptions import ValidationError
from odoo.addons.base.models.ir_ui_view import MOVABLE_BRANDING

_logger = logging.getLogger(__name__)

EDITING_ATTRIBUTES = MOVABLE_BRANDING + [
    'data-oe-type',
    'data-oe-expression',
    'data-oe-translation-id',
    'data-note-id'
]


class IrUiView(models.Model):
    _inherit = 'ir.ui.view'

    def _get_cleaned_non_editing_attributes(self, attributes):
        """
        Returns a new mapping of attributes -> value without the parts that are
        not meant to be saved (branding, editing classes, ...). Note that
        classes are meant to be cleaned on the client side before saving as
        mostly linked to the related options (so we are not supposed to know
        which to remove here).

        :param attributes: a mapping of attributes -> value
        :return: a new mapping of attributes -> value
        """
        attributes = {k: v for k, v in attributes if k not in EDITING_ATTRIBUTES}
        if 'class' in attributes:
            classes = attributes['class'].split()
            attributes['class'] = ' '.join([c for c in classes if c != 'o_editable'])
        if attributes.get('contenteditable') == 'true':
            del attributes['contenteditable']
        return attributes

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

        try:
            value = converter.from_html(Model, Model._fields[field], el)
        except ValueError:
            raise ValidationError(_("Invalid field value for %s: %s", Model._fields[field].string, el.text_content().strip()))

        if value is not None:
            # TODO: batch writes?
            record = Model.browse(int(el.get('data-oe-id')))
            if not self.env.context.get('lang') and self.get_default_lang_code():
                record.with_context(lang=self.get_default_lang_code()).write({field: value})
            else:
                record.write({field: value})

            if callable(Model._fields[field].translate):
                self._copy_custom_snippet_translations(record, field)

    def save_oe_structure(self, el):
        self.ensure_one()

        if el.get('id') in self.key:
            # Do not inherit if the oe_structure already has its own inheriting view
            return False

        arch = etree.Element('data')
        xpath = etree.Element('xpath', expr="//*[hasclass('oe_structure')][@id='{}']".format(el.get('id')), position="replace")
        arch.append(xpath)
        attributes = self._get_cleaned_non_editing_attributes(el.attrib.items())
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
        oe_structure_view = self.env['ir.ui.view'].create(vals)
        self._copy_custom_snippet_translations(oe_structure_view, 'arch_db')

        return True

    @api.model
    def _copy_custom_snippet_translations(self, record, html_field):
        """ Given a ``record`` and its HTML ``field``, detect any
        usage of a custom snippet and copy its translations.
        """
        lang_value = record[html_field]
        if not lang_value:
            return

        tree = html.fromstring(lang_value)
        for custom_snippet_el in tree.xpath('//*[hasclass("s_custom_snippet")]'):
            custom_snippet_name = custom_snippet_el.get('data-name')
            custom_snippet_view = self.search([('name', '=', custom_snippet_name)], limit=1)
            if custom_snippet_view:
                self._copy_field_terms_translations(custom_snippet_view, 'arch_db', record, html_field)

    @api.model
    def _copy_field_terms_translations(self, record_from, name_field_from, record_to, name_field_to):
        """ Copy the terms translation from a record/field ``Model1.Field1``
        to a (possibly) completely different record/field ``Model2.Field2``.

        For instance, copy the translations of a
        ``product.template.html_description`` field to a ``ir.ui.view.arch_db``
        field.

        The method takes care of read and write access of both records/fields.
        """
        record_to.check_access_rights('write')
        record_to.check_access_rule('write')
        record_to.check_field_access_rights('write', [name_field_to])

        # This will also implicitly check for `read` access rights
        if not record_from[name_field_from] or not record_to[name_field_to]:
            return

        field_from = record_from._fields[name_field_from]
        field_to = record_to._fields[name_field_to]
        error_callable_msg = "'translate' property of field %r is not callable"
        if not callable(field_from.translate):
            raise ValueError(error_callable_msg % field_from)
        if not callable(field_to.translate):
            raise ValueError(error_callable_msg % field_to)
        if not field_to.store:
            raise ValueError("Field %r is not stored" % field_to)

        lang_env = self.env.lang or 'en_US'
        langs = set(lang for lang, _ in self.env['res.lang'].get_installed())

        # 1. Get translations
        record_from.flush_model([name_field_from])
        existing_translation_dictionary = field_to.get_translation_dictionary(
            record_to[name_field_to],
            {lang: record_to.with_context(prefetch_langs=True, lang=lang)[name_field_to] for lang in langs if lang != lang_env}
        )
        extra_translation_dictionary = field_from.get_translation_dictionary(
            record_from[name_field_from],
            {lang: record_from.with_context(prefetch_langs=True, lang=lang)[name_field_from] for lang in langs if lang != lang_env}
        )
        existing_translation_dictionary.update(extra_translation_dictionary)
        translation_dictionary = existing_translation_dictionary

        # The `en_US` jsonb value should always be set, even if english is not
        # installed. If we don't do this, the custom snippet `arch_db` will only
        # have a `fr_BE` key but no `en_US` key.
        langs.add('en_US')

        # 2. Set translations
        new_value = {
            lang: field_to.translate(lambda term: translation_dictionary.get(term, {}).get(lang), record_to[name_field_to])
            for lang in langs
        }
        record_to.env.cache.update_raw(record_to, field_to, [new_value], dirty=True)
        # Call `write` to trigger compute etc (`modified()`)
        record_to[name_field_to] = new_value[lang_env]

    @api.model
    def _save_oe_structure_hook(self):
        return {}

    @api.model
    def _pretty_arch(self, arch):
        # TODO: Remove this method in 16.3.
        return etree.tostring(arch, encoding='unicode')

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
        return all(self._are_archs_equal(arch1, arch2) for arch1, arch2 in zip(arch1, arch2))

    @api.model
    def _get_allowed_root_attrs(self):
        return ['style', 'class']

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

        # We need to replace some attrib for styles changes on the root element
        for attribute in self._get_allowed_root_attrs():
            if attribute in replacement.attrib:
                root.attrib[attribute] = replacement.attrib[attribute]

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
            self._copy_custom_snippet_translations(self, 'arch_db')

    @api.model
    def _view_get_inherited_children(self, view):
        if self._context.get('no_primary_children', False):
            original_hierarchy = self._context.get('__views_get_original_hierarchy', [])
            return view.inherit_children_ids.filtered(lambda extension: extension.mode != 'primary' or extension.id in original_hierarchy)
        return view.inherit_children_ids

    @api.model
    def _view_obj(self, view_id):
        if isinstance(view_id, str):
            return self.search([('key', '=', view_id)], limit=1) or self.env.ref(view_id)
        elif isinstance(view_id, int):
            return self.browse(view_id)
        # It can already be a view object when called by '_views_get()' that is calling '_view_obj'
        # for it's inherit_children_ids, passing them directly as object record.
        return view_id

    # Returns all views (called and inherited) related to a view
    # Used by translation mechanism, SEO and optional templates

    @api.model
    def _views_get(self, view_id, get_children=True, bundles=False, root=True, visited=None):
        """ For a given view ``view_id``, should return:
                * the view itself (starting from its top most parent)
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
        original_hierarchy = self._context.get('__views_get_original_hierarchy', [])
        while root and view.inherit_id:
            original_hierarchy.append(view.id)
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
                views_to_return += self._views_get(called_view, get_children=get_children, bundles=bundles, visited=visited + views_to_return.ids)

        if not get_children:
            return views_to_return

        extensions = self._view_get_inherited_children(view)

        # Keep children in a deterministic order regardless of their applicability
        for extension in extensions.sorted(key=lambda v: v.id):
            # only return optional grandchildren if this child is enabled
            if extension.id not in visited:
                for ext_view in self._views_get(extension, get_children=extension.active, root=False, visited=visited + views_to_return.ids):
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
        new_context = {
            **self._context,
            'active_test': False,
        }
        new_context.pop('lang', None)
        View = self.with_context(new_context)
        views = View._views_get(key, bundles=bundles)
        return views.filtered(lambda v: not v.groups_id or len(user_groups.intersection(v.groups_id)))

    # --------------------------------------------------------------------------
    # Snippet saving
    # --------------------------------------------------------------------------

    @api.model
    def _get_snippet_addition_view_key(self, template_key, key):
        return '%s.%s' % (template_key, key)

    @api.model
    def _snippet_save_view_values_hook(self):
        return {}

    def _find_available_name(self, name, used_names):
        attempt = 1
        candidate_name = name
        while candidate_name in used_names:
            attempt += 1
            candidate_name = f"{name} ({attempt})"
        return candidate_name

    @api.model
    def save_snippet(self, name, arch, template_key, snippet_key, thumbnail_url):
        """
        Saves a new snippet arch so that it appears with the given name when
        using the given snippets template.

        :param name: the name of the snippet to save
        :param arch: the html structure of the snippet to save
        :param template_key: the key of the view regrouping all snippets in
            which the snippet to save is meant to appear
        :param snippet_key: the key (without module part) to identify
            the snippet from which the snippet to save originates
        :param thumbnail_url: the url of the thumbnail to use when displaying
            the snippet to save
        """
        app_name = template_key.split('.')[0]
        snippet_key = '%s_%s' % (snippet_key, uuid.uuid4().hex)
        full_snippet_key = '%s.%s' % (app_name, snippet_key)

        # find available name
        current_website = self.env['website'].browse(self._context.get('website_id'))
        website_domain = current_website.website_domain()
        used_names = self.search(expression.AND([
            [('name', '=like', '%s%%' % name)], website_domain
        ])).mapped('name')
        name = self._find_available_name(name, used_names)

        # html to xml to add '/' at the end of self closing tags like br, ...
        arch_tree = html.fromstring(arch)
        attributes = self._get_cleaned_non_editing_attributes(arch_tree.attrib.items())
        for attr in arch_tree.attrib:
            if attr in attributes:
                arch_tree.attrib[attr] = attributes[attr]
            else:
                del arch_tree.attrib[attr]
        xml_arch = etree.tostring(arch_tree, encoding='utf-8')
        new_snippet_view_values = {
            'name': name,
            'key': full_snippet_key,
            'type': 'qweb',
            'arch': xml_arch,
        }
        new_snippet_view_values.update(self._snippet_save_view_values_hook())
        custom_snippet_view = self.create(new_snippet_view_values)
        model = self._context.get('model')
        field = self._context.get('field')
        if field == 'arch':
            # Special case for `arch` which is a kind of related (through a
            # compute) to `arch_db` but which is hosting XML/HTML content while
            # being a char field.. Which is then messing around with the
            # `get_translation_dictionary` call, returning XML instead of
            # strings
            field = 'arch_db'
        res_id = self._context.get('resId')
        if model and field and res_id:
            self._copy_field_terms_translations(
                self.env[model].browse(int(res_id)),
                field,
                custom_snippet_view,
                'arch_db',
            )

        custom_section = self.search([('key', '=', template_key)])
        snippet_addition_view_values = {
            'name': name + ' Block',
            'key': self._get_snippet_addition_view_key(template_key, snippet_key),
            'inherit_id': custom_section.id,
            'type': 'qweb',
            'arch': """
                <data inherit_id="%s">
                    <xpath expr="//div[@id='snippet_custom']" position="attributes">
                        <attribute name="class" remove="d-none" separator=" "/>
                    </xpath>
                    <xpath expr="//div[@id='snippet_custom_body']" position="inside">
                        <t t-snippet="%s" t-thumbnail="%s"/>
                    </xpath>
                </data>
            """ % (template_key, full_snippet_key, thumbnail_url),
        }
        snippet_addition_view_values.update(self._snippet_save_view_values_hook())
        self.create(snippet_addition_view_values)

    @api.model
    def rename_snippet(self, name, view_id, template_key):
        snippet_view = self.browse(view_id)
        key = snippet_view.key.split('.')[1]
        custom_key = self._get_snippet_addition_view_key(template_key, key)
        snippet_addition_view = self.search([('key', '=', custom_key)])
        if snippet_addition_view:
            snippet_addition_view.name = name + ' Block'
        snippet_view.name = name

    @api.model
    def delete_snippet(self, view_id, template_key):
        snippet_view = self.browse(view_id)
        key = snippet_view.key.split('.')[1]
        custom_key = self._get_snippet_addition_view_key(template_key, key)
        snippet_addition_view = self.search([('key', '=', custom_key)])
        (snippet_addition_view | snippet_view).unlink()

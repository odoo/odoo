import uuid
from lxml import etree, html

from odoo import api, models
from odoo.addons.base.models.ir_ui_view import MOVABLE_BRANDING
from odoo.fields import Domain

EDITING_ATTRIBUTES = MOVABLE_BRANDING + [
    'data-oe-type',
    'data-oe-expression',
    'data-oe-translation-id',
    'data-note-id'
]


class IrUiView(models.Model):
    _inherit = "ir.ui.view"

    @api.model
    def delete_snippet(self, view_id, template_key):
        snippet_view = self.browse(view_id)
        key = snippet_view.key.split('.')[1]
        custom_key = self._get_snippet_addition_view_key(template_key, key)
        snippet_addition_view = self.search([('key', '=', custom_key)])
        (snippet_addition_view | snippet_view).unlink()

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

        used_names = self.env['ir.ui.view'].search(self._get_used_names_domain(name)).mapped("name")
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
        model = self.env.context.get('model')
        field = self.env.context.get('field')
        if field == 'arch':
            # Special case for `arch` which is a kind of related (through a
            # compute) to `arch_db` but which is hosting XML/HTML content while
            # being a char field.. Which is then messing around with the
            # `get_translation_dictionary` call, returning XML instead of
            # strings
            field = 'arch_db'
        res_id = self.env.context.get('resId')
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
                    <xpath expr="//snippets[@id='snippet_custom']" position="inside">
                        <t t-snippet="%s" t-thumbnail="%s"/>
                    </xpath>
                </data>
            """ % (template_key, full_snippet_key, thumbnail_url),
        }
        snippet_addition_view_values.update(self._snippet_save_view_values_hook())
        self.create(snippet_addition_view_values)
        return name

    @api.model
    def _copy_field_terms_translations(self, records_from, name_field_from, record_to, name_field_to):
        """ Copy model terms translations from ``records_from.name_field_from``
        to ``record_to.name_field_to`` for all activated languages if the term
        in ``record_to.name_field_to`` is untranslated (the term matches the
        one in the current language).

        For instance, copy the translations of a
        ``product.template.html_description`` field to a ``ir.ui.view.arch_db``
        field.

        The method takes care of read and write access of both records/fields.
        """
        record_to.check_access('write')
        field_from = records_from._fields[name_field_from]
        field_to = record_to._fields[name_field_to]
        record_to._check_field_access(field_to, 'write')

        error_callable_msg = "'translate' property of field %r is not callable"
        if not callable(field_from.translate):
            raise TypeError(error_callable_msg % field_from)
        if not callable(field_to.translate):
            raise TypeError(error_callable_msg % field_to)
        if not field_to.store:
            raise ValueError("Field %r is not stored" % field_to)

        # This will also implicitly check for `read` access rights
        if not record_to[name_field_to] or not any(records_from.mapped(name_field_from)):
            return

        lang_env = self.env.lang or 'en_US'
        langs = {lang for lang, _ in self.env['res.lang'].get_installed()}

        # 1. Get translations
        records_from.flush_model([name_field_from])
        existing_translation_dictionary = field_to.get_translation_dictionary(
            record_to[name_field_to],
            {lang: record_to.with_context(prefetch_langs=True, lang=lang)[name_field_to] for lang in langs if lang != lang_env}
        )
        extra_translation_dictionary = {}
        for record_from in records_from:
            extra_translation_dictionary.update(field_from.get_translation_dictionary(
                record_from[name_field_from],
                {lang: record_from.with_context(prefetch_langs=True, lang=lang)[name_field_from] for lang in langs if lang != lang_env}
            ))
        for term, extra_translation_values in extra_translation_dictionary.items():
            existing_translation_values = existing_translation_dictionary.setdefault(term, {})
            # Update only default translation values that aren't customized by the user.
            for lang, extra_translation in extra_translation_values.items():
                if existing_translation_values.get(lang, term) == term:
                    existing_translation_values[lang] = extra_translation
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
    def _find_available_name(self, name, used_names):
        attempt = 1
        candidate_name = name
        while candidate_name in used_names:
            attempt += 1
            candidate_name = f"{name} ({attempt})"
        return candidate_name

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
        if attributes.get('contenteditable') == 'true':
            del attributes['contenteditable']
        return attributes

    @api.model
    def _get_snippet_addition_view_key(self, template_key, key):
        return '%s.%s' % (template_key, key)

    @api.model
    def _get_used_names_domain(self, name):
        return Domain('name', '=like', '%s%%' % name)

    @api.model
    def _snippet_save_view_values_hook(self):
        return {}

from __future__ import annotations

import collections.abc
import logging
import typing
from collections import defaultdict
from difflib import get_close_matches, unified_diff
from hashlib import sha256
from operator import attrgetter

from markupsafe import Markup
from markupsafe import escape as markup_escape
from psycopg2.extras import Json as PsycopgJson

from odoo.exceptions import AccessError, UserError
from odoo.netsvc import COLOR_PATTERN, DEFAULT, GREEN, RED, ColoredFormatter
from odoo.tools import SQL, html_normalize, html_sanitize, html2plaintext, is_html_empty, plaintext2html, sql
from odoo.tools.misc import OrderedSet, SENTINEL, Sentinel
from odoo.tools.sql import pattern_to_translated_trigram_pattern, pg_varchar, value_to_translated_trigram_pattern
from odoo.tools.translate import html_translate

from .fields import Field, _logger
from .utils import COLLECTION_TYPES, SQL_OPERATORS

if typing.TYPE_CHECKING:
    from .models import BaseModel
    from odoo.tools import Query

if typing.TYPE_CHECKING:
    from collections.abc import Callable


class BaseString(Field[str | typing.Literal[False]]):
    """ Abstract class for string fields. """
    translate: bool | Callable[[Callable[[str], str], str], str] = False  # whether the field is translated
    size = None                         # maximum size of values (deprecated)
    is_text = True
    falsy_value = ''

    def __init__(self, string: str | Sentinel = SENTINEL, **kwargs):
        # translate is either True, False, or a callable
        if 'translate' in kwargs and not callable(kwargs['translate']):
            kwargs['translate'] = bool(kwargs['translate'])
        super().__init__(string=string, **kwargs)

    _related_translate = property(attrgetter('translate'))

    def _description_translate(self, env):
        return bool(self.translate)

    def setup_related(self, model):
        super().setup_related(model)
        if self.store and self.translate:
            _logger.warning("Translated stored related field (%s) will not be computed correctly in all languages", self)

    def get_depends(self, model):
        if self.translate and self.store:
            dep, dep_ctx = super().get_depends(model)
            if dep_ctx:
                _logger.warning("Translated stored fields (%s) cannot depend on context", self)
            return dep, ()
        return super().get_depends(model)

    def _convert_db_column(self, model, column):
        # specialized implementation for converting from/to translated fields
        if self.translate or column['udt_name'] == 'jsonb':
            sql.convert_column_translatable(model.env.cr, model._table, self.name, self.column_type[1])
        else:
            sql.convert_column(model.env.cr, model._table, self.name, self.column_type[1])

    def get_trans_terms(self, value):
        """ Return the sequence of terms to translate found in `value`. """
        if not callable(self.translate):
            return [value] if value else []
        terms = []
        self.translate(terms.append, value)
        return terms

    def get_text_content(self, term):
        """ Return the textual content for the given term. """
        func = getattr(self.translate, 'get_text_content', lambda term: term)
        return func(term)

    def convert_to_column(self, value, record, values=None, validate=True):
        return self.convert_to_cache(value, record, validate)

    def convert_to_column_insert(self, value, record, values=None, validate=True):
        if self.translate:
            value = self.convert_to_column(value, record, values, validate)
            if value is None:
                return None
            return PsycopgJson({'en_US': value, record.env.lang or 'en_US': value})
        return super().convert_to_column_insert(value, record, values, validate)

    def get_column_update(self, record):
        if self.translate:
            assert self not in record.env._field_depends_context, f"translated field {self} cannot depend on context"
            value = record.env.transaction.field_data[self][record.id]
            return PsycopgJson(value) if value else None
        return super().get_column_update(record)

    def convert_to_cache(self, value, record, validate=True):
        if value is None or value is False:
            return None

        if isinstance(value, bytes):
            s = value.decode()
        else:
            s = str(value)
        value = s[:self.size]
        if validate and callable(self.translate):
            # pylint: disable=not-callable
            value = self.translate(lambda t: None, value)
        return value

    def convert_to_record(self, value, record):
        if value is None:
            return False
        if not self.translate:
            return value
        if isinstance(value, dict):
            lang = self.translation_lang(record.env)
            # raise a KeyError for the __get__ function
            value = value[lang]
        if (
            callable(self.translate)
            and record.env.context.get('edit_translations')
            and self.get_trans_terms(value)
        ):
            base_lang = record._get_base_lang()
            lang = record.env.lang or 'en_US'

            if lang != base_lang:
                base_value = record.with_context(edit_translations=None, check_translations=True, lang=base_lang)[self.name]
                base_terms_iter = iter(self.get_trans_terms(base_value))
                get_base = lambda term: next(base_terms_iter)
            else:
                get_base = lambda term: term

            delay_translation = value != record.with_context(edit_translations=None, check_translations=None, lang=lang)[self.name]

            # use a wrapper to let the frontend js code identify each term and
            # its metadata in the 'edit_translations' context
            def translate_func(term):
                source_term = get_base(term)
                translation_state = 'translated' if lang == base_lang or source_term != term else 'to_translate'
                translation_source_sha = sha256(source_term.encode()).hexdigest()
                return (
                    '<span '
                        f'''{'class="o_delay_translation" ' if delay_translation else ''}'''
                        f'data-oe-model="{markup_escape(record._name)}" '
                        f'data-oe-id="{markup_escape(record.id)}" '
                        f'data-oe-field="{markup_escape(self.name)}" '
                        f'data-oe-translation-state="{translation_state}" '
                        f'data-oe-translation-source-sha="{translation_source_sha}"'
                    '>'
                        f'{term}'
                    '</span>'
                )
            # pylint: disable=not-callable
            value = self.translate(translate_func, value)
        return value

    def convert_to_write(self, value, record):
        return value

    def get_translation_dictionary(self, from_lang_value, to_lang_values):
        """ Build a dictionary from terms in from_lang_value to terms in to_lang_values

        :param str from_lang_value: from xml/html
        :param dict to_lang_values: {lang: lang_value}

        :return: {from_lang_term: {lang: lang_term}}
        :rtype: dict
        """

        from_lang_terms = self.get_trans_terms(from_lang_value)
        dictionary = defaultdict(lambda: defaultdict(dict))
        if not from_lang_terms:
            return dictionary
        dictionary.update({from_lang_term: defaultdict(dict) for from_lang_term in from_lang_terms})

        for lang, to_lang_value in to_lang_values.items():
            to_lang_terms = self.get_trans_terms(to_lang_value)
            if len(from_lang_terms) != len(to_lang_terms):
                for from_lang_term in from_lang_terms:
                    dictionary[from_lang_term][lang] = from_lang_term
            else:
                for from_lang_term, to_lang_term in zip(from_lang_terms, to_lang_terms):
                    dictionary[from_lang_term][lang] = to_lang_term
        return dictionary

    def _get_stored_translations(self, record):
        """
        : return: {'en_US': 'value_en_US', 'fr_FR': 'French'}
        """
        # assert (self.translate and self.store and record)
        record.flush_recordset([self.name])
        cr = record.env.cr
        cr.execute(SQL(
            "SELECT %s FROM %s WHERE id = %s",
            SQL.identifier(self.name),
            SQL.identifier(record._table),
            record.id,
        ))
        res = cr.fetchone()
        return res[0] if res else None

    def translation_lang(self, env):
        return (env.lang or 'en_US') if self.translate is True else env._lang

    def get_translation_fallback_langs(self, env):
        lang = self.translation_lang(env)
        if lang == '_en_US':
            return '_en_US', 'en_US'
        if lang == 'en_US':
            return ('en_US',)
        if lang.startswith('_'):
            return lang, lang[1:], '_en_US', 'en_US'
        return lang, 'en_US'

    def _get_cache_impl(self, env):
        cache = super()._get_cache_impl(env)
        if not self.translate or env.context.get('prefetch_langs'):
            return cache
        lang = self.translation_lang(env)
        return LangProxyDict(self, cache, lang)

    def _cache_missing_ids(self, records):
        if self.translate and records.env.context.get('prefetch_langs'):
            # we always need to fetch the current language in the cache
            records = records.with_context(prefetch_langs=False)
        return super()._cache_missing_ids(records)

    def _to_prefetch(self, record):
        if self.translate and record.env.context.get('prefetch_langs'):
            # we always need to fetch the current language in the cache
            return super()._to_prefetch(record.with_context(prefetch_langs=False)).with_env(record.env)
        return super()._to_prefetch(record)

    def _insert_cache(self, records, values):
        if not self.translate:
            super()._insert_cache(records, values)
            return

        assert self not in records.env._field_depends_context, f"translated field {self} cannot depend on context"
        env = records.env
        field_cache = env.transaction.field_data[self]
        if env.context.get('prefetch_langs'):
            installed = [lang for lang, _ in env['res.lang'].get_installed()]
            langs = OrderedSet[str](installed + ['en_US'])
            u_langs: list[str] = [f'_{lang}' for lang in langs] if self.translate is not True and env._lang.startswith('_') else []
            for id_, val in zip(records._ids, values):
                if val is None:
                    field_cache.setdefault(id_, None)
                else:
                    if u_langs:  # fallback missing _lang to lang if exists
                        val.update({f'_{k}': v for k, v in val.items() if k in langs and f'_{k}' not in val})
                    field_cache[id_] = {
                        **dict.fromkeys(langs, val['en_US']),  # fallback missing lang to en_US
                        **dict.fromkeys(u_langs, val.get('_en_US')),  # fallback missing _lang to _en_US
                        **val
                    }
        else:
            lang = self.translation_lang(env)
            for id_, val in zip(records._ids, values):
                if val is None:
                    field_cache.setdefault(id_, None)
                else:
                    cache_value = field_cache.setdefault(id_, {})
                    if cache_value is not None:
                        cache_value.setdefault(lang, val)

    def _update_cache(self, records, cache_value, dirty=False):
        if self.translate and cache_value is not None and records.env.context.get('prefetch_langs'):
            assert isinstance(cache_value, dict), f"invalid cache value for {self}"
            if len(records) > 1:
                # new dict for each record
                for record in records:
                    super()._update_cache(record, dict(cache_value), dirty)
                return
        super()._update_cache(records, cache_value, dirty)

    def write(self, records, value):
        if not self.translate or value is False or value is None:
            super().write(records, value)
            return
        cache_value = self.convert_to_cache(value, records)
        records = self._filter_not_equal(records, cache_value)
        if not records:
            return
        field_cache = self._get_cache(records.env)
        dirty_ids = records.env._field_dirty.get(self, ())

        # flush dirty None values
        dirty_records = records.filtered(lambda rec: rec.id in dirty_ids)
        if any(field_cache.get(record_id, SENTINEL) is None for record_id in dirty_records._ids):
            dirty_records.flush_recordset([self.name])

        dirty = self.store and any(records._ids)
        lang = self.translation_lang(records.env)

        # not dirty fields
        if not dirty:
            if self.compute and self.inverse:
                # invalidate the values in other languages to force their recomputation
                self._update_cache(records.with_context(prefetch_langs=True), {lang: cache_value}, dirty=False)
            else:
                self._update_cache(records, cache_value, dirty=False)
            return

        # model translation
        if not callable(self.translate):
            # invalidate clean fields because them may contain fallback value
            clean_records = records.filtered(lambda rec: rec.id not in dirty_ids)
            clean_records.invalidate_recordset([self.name])
            self._update_cache(records, cache_value, dirty=True)
            if lang != 'en_US' and not records.env['res.lang']._get_data(code='en_US'):
                # if 'en_US' is not active, we always write en_US to make sure value_en is meaningful
                self._update_cache(records.with_context(lang='en_US'), cache_value, dirty=True)
            return

        # model term translation
        new_translations_list = []
        new_terms = set(self.get_trans_terms(cache_value))
        delay_translations = records.env.context.get('delay_translations')
        for record in records:
            # shortcut when no term needs to be translated
            if not new_terms:
                new_translations_list.append({'en_US': cache_value, lang: cache_value})
                continue
            # _get_stored_translations can be refactored and prefetches translations for multi records,
            # but it is really rare to write the same non-False/None/no-term value to multi records
            stored_translations = self._get_stored_translations(record)
            if not stored_translations:
                new_translations_list.append({'en_US': cache_value, lang: cache_value})
                continue
            old_translations = {
                k: stored_translations.get(f'_{k}', v)
                for k, v in stored_translations.items()
                if not k.startswith('_')
            }
            from_lang_value = old_translations.pop(lang, old_translations['en_US'])
            translation_dictionary = self.get_translation_dictionary(from_lang_value, old_translations)
            text2terms = defaultdict(list)
            for term in new_terms:
                if term_text := self.get_text_content(term):
                    text2terms[term_text].append(term)

            is_text = self.translate.is_text if hasattr(self.translate, 'is_text') else lambda term: True
            term_adapter = self.translate.term_adapter if hasattr(self.translate, 'term_adapter') else None
            for old_term in list(translation_dictionary.keys()):
                if old_term not in new_terms:
                    old_term_text = self.get_text_content(old_term)
                    matches = get_close_matches(old_term_text, text2terms, 1, 0.9)
                    if matches:
                        closest_term = get_close_matches(old_term, text2terms[matches[0]], 1, 0)[0]
                        if closest_term in translation_dictionary:
                            continue
                        old_is_text = is_text(old_term)
                        closest_is_text = is_text(closest_term)
                        if old_is_text or not closest_is_text:
                            if not closest_is_text and records.env.context.get("install_mode") and lang == 'en_US' and term_adapter:
                                adapter = term_adapter(closest_term)
                                if adapter(old_term) is None:  # old term and closest_term have different structures
                                     continue
                                translation_dictionary[closest_term] = {k: adapter(v) for k, v in translation_dictionary.pop(old_term).items()}
                            else:
                                translation_dictionary[closest_term] = translation_dictionary.pop(old_term)
            # pylint: disable=not-callable
            new_translations = {
                l: self.translate(lambda term: translation_dictionary.get(term, {l: None})[l], cache_value)
                for l in old_translations.keys()
            }
            if delay_translations:
                new_store_translations = stored_translations
                new_store_translations.update({f'_{k}': v for k, v in new_translations.items()})
                new_store_translations.pop(f'_{lang}', None)
            else:
                new_store_translations = new_translations
            new_store_translations[lang] = cache_value

            if not records.env['res.lang']._get_data(code='en_US'):
                new_store_translations['en_US'] = cache_value
                new_store_translations.pop('_en_US', None)
            new_translations_list.append(new_store_translations)
        for record, new_translation in zip(records.with_context(prefetch_langs=True), new_translations_list, strict=True):
            self._update_cache(record, new_translation, dirty=True)

    def to_sql(self, model: BaseModel, alias: str) -> SQL:
        sql_field = super().to_sql(model, alias)
        if self.translate and not model.env.context.get('prefetch_langs'):
            langs = self.get_translation_fallback_langs(model.env)
            sql_field_langs = [SQL("%s->>%s", sql_field, lang) for lang in langs]
            if len(sql_field_langs) == 1:
                return sql_field_langs[0]
            return SQL("COALESCE(%s)", SQL(", ").join(sql_field_langs))
        return sql_field

    def expression_getter(self, field_expr):
        if field_expr != 'display_name.no_error':
            return super().expression_getter(field_expr)

        # when searching by display_name, don't raise AccessError but return an
        # empty value instead
        get_display_name = super().expression_getter('display_name')

        def getter(record):
            try:
                return get_display_name(record)
            except AccessError:
                return ''

        return getter

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        # build the condition
        if self.translate and model.env.context.get('prefetch_langs'):
            model = model.with_context(prefetch_langs=False)
        base_condition = super().condition_to_sql(field_expr, operator, value, model, alias, query)

        # faster SQL for index trigrams
        if (
            self.translate
            and value
            and operator in ('in', 'like', 'ilike', '=like', '=ilike')
            and self.index == 'trigram'
            and model.pool.has_trigram
            and (
                isinstance(value, str)
                or (isinstance(value, COLLECTION_TYPES) and all(isinstance(v, str) for v in value))
            )
        ):
            # a prefilter using trigram index to speed up '=', 'like', 'ilike'
            # '!=', '<=', '<', '>', '>=', 'in', 'not in', 'not like', 'not ilike' cannot use this trick
            if operator == 'in' and len(value) == 1:
                value = value_to_translated_trigram_pattern(next(iter(value)))
            elif operator != 'in':
                value = pattern_to_translated_trigram_pattern(value)
            else:
                value = '%'

            if value == '%':
                return base_condition

            raw_sql_field = self.to_sql(model.with_context(prefetch_langs=True), alias)
            sql_left = SQL("jsonb_path_query_array(%s, '$.*')::text", raw_sql_field)
            sql_operator = SQL_OPERATORS['like' if operator == 'in' else operator]
            sql_right = SQL("%s", self.convert_to_column(value, model, validate=False))
            unaccent = model.env.registry.unaccent
            return SQL(
                "(%s%s%s AND %s)",
                unaccent(sql_left),
                sql_operator,
                unaccent(sql_right),
                base_condition,
            )
        return base_condition


class Char(BaseString):
    """ Basic string field, can be length-limited, usually displayed as a
    single-line string in clients.

    :param int size: the maximum size of values stored for that field

    :param bool trim: states whether the value is trimmed or not (by default,
        ``True``). Note that the trim operation is applied by both the server code and the web client
        This ensures consistent behavior between imported data and UI-entered data.

        - The web client trims user input during in write/create flows in UI.
        - The server trims values during import (in `base_import`) to avoid discrepancies between
          trimmed form inputs and stored DB values.

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    :type translate: bool or callable
    """
    type = 'char'
    trim: bool = True                   # whether value is trimmed (only by web client and base_import)

    def _setup_attrs__(self, model_class, name):
        super()._setup_attrs__(model_class, name)
        assert self.size is None or isinstance(self.size, int), \
            "Char field %s with non-integer size %r" % (self, self.size)

    @property
    def _column_type(self):
        return ('varchar', pg_varchar(self.size))

    def update_db_column(self, model, column):
        if (
            column and self.column_type[0] == 'varchar' and
            column['udt_name'] == 'varchar' and column['character_maximum_length'] and
            (self.size is None or column['character_maximum_length'] < self.size)
        ):
            # the column's varchar size does not match self.size; convert it
            sql.convert_column(model.env.cr, model._table, self.name, self.column_type[1])
        super().update_db_column(model, column)

    _related_size = property(attrgetter('size'))
    _related_trim = property(attrgetter('trim'))
    _description_size = property(attrgetter('size'))
    _description_trim = property(attrgetter('trim'))

    def get_depends(self, model):
        depends, depends_context = super().get_depends(model)

        # display_name may depend on context['lang'] (`test_lp1071710`)
        if (
            self.name == 'display_name'
            and self.compute
            and not self.store
            and model._rec_name
            and model._fields[model._rec_name].base_field.translate
            and 'lang' not in depends_context
        ):
            depends_context = [*depends_context, 'lang']

        return depends, depends_context


class Text(BaseString):
    """ Very similar to :class:`Char` but used for longer contents, does not
    have a size and usually displayed as a multiline text box.

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    :type translate: bool or callable
    """
    type = 'text'
    _column_type = ('text', 'text')


class Html(BaseString):
    """ Encapsulates an html code content.

    :param bool sanitize: whether value must be sanitized (default: ``True``)
    :param bool sanitize_overridable: whether the sanitation can be bypassed by
        the users part of the `base.group_sanitize_override` group (default: ``False``)
    :param bool sanitize_tags: whether to sanitize tags
        (only a white list of attributes is accepted, default: ``True``)
    :param bool sanitize_attributes: whether to sanitize attributes
        (only a white list of attributes is accepted, default: ``True``)
    :param bool sanitize_style: whether to sanitize style attributes (default: ``False``)
    :param bool sanitize_conditional_comments: whether to kill conditional comments. (default: ``True``)
    :param bool sanitize_output_method: whether to sanitize using html or xhtml (default: ``html``)
    :param bool strip_style: whether to strip style attributes
        (removed and therefore not sanitized, default: ``False``)
    :param bool strip_classes: whether to strip classes attributes (default: ``False``)
    """
    type = 'html'
    _column_type = ('text', 'text')

    sanitize: bool = True                     # whether value must be sanitized
    sanitize_overridable: bool = False        # whether the sanitation can be bypassed by the users part of the `base.group_sanitize_override` group
    sanitize_tags: bool = True                # whether to sanitize tags (only a white list of attributes is accepted)
    sanitize_attributes: bool = True          # whether to sanitize attributes (only a white list of attributes is accepted)
    sanitize_style: bool = False              # whether to sanitize style attributes
    sanitize_form: bool = True                # whether to sanitize forms
    sanitize_conditional_comments: bool = True  # whether to kill conditional comments. Otherwise keep them but with their content sanitized.
    sanitize_output_method: str = 'html'      # whether to sanitize using html or xhtml
    strip_style: bool = False                 # whether to strip style attributes (removed and therefore not sanitized)
    strip_classes: bool = False               # whether to strip classes attributes

    def _get_attrs(self, model_class, name):
        # called by _setup_attrs__(), working together with BaseString._setup_attrs__()
        attrs = super()._get_attrs(model_class, name)
        # Shortcut for common sanitize options
        # Outgoing and incoming emails should not be sanitized with the same options.
        # e.g. conditional comments: no need to keep conditional comments for incoming emails,
        # we do not need this Microsoft Outlook client feature for emails displayed Odoo's web client.
        # While we need to keep them in mail templates and mass mailings, because they could be rendered in Outlook.
        if attrs.get('sanitize') == 'email_outgoing':
            attrs['sanitize'] = True
            attrs.update({key: value for key, value in {
                'sanitize_tags': False,
                'sanitize_attributes': False,
                'sanitize_conditional_comments': False,
                'sanitize_output_method': 'xml',
            }.items() if key not in attrs})
        # Translated sanitized html fields must use html_translate or a callable.
        # `elif` intended, because HTML fields with translate=True and sanitize=False
        # where not using `html_translate` before and they must remain without `html_translate`.
        # Otherwise, breaks `--test-tags .test_render_field`, for instance.
        elif attrs.get('translate') is True and attrs.get('sanitize', True):
            attrs['translate'] = html_translate
        return attrs

    _related_sanitize = property(attrgetter('sanitize'))
    _related_sanitize_tags = property(attrgetter('sanitize_tags'))
    _related_sanitize_attributes = property(attrgetter('sanitize_attributes'))
    _related_sanitize_style = property(attrgetter('sanitize_style'))
    _related_strip_style = property(attrgetter('strip_style'))
    _related_strip_classes = property(attrgetter('strip_classes'))

    _description_sanitize = property(attrgetter('sanitize'))
    _description_sanitize_tags = property(attrgetter('sanitize_tags'))
    _description_sanitize_attributes = property(attrgetter('sanitize_attributes'))
    _description_sanitize_style = property(attrgetter('sanitize_style'))
    _description_strip_style = property(attrgetter('strip_style'))
    _description_strip_classes = property(attrgetter('strip_classes'))

    def convert_to_column(self, value, record, values=None, validate=True):
        value = self._convert(value, record, validate=validate)
        return super().convert_to_column(value, record, values, validate=False)

    def convert_to_cache(self, value, record, validate=True):
        return self._convert(value, record, validate)

    def _convert(self, value, record, validate):
        if value is None or value is False:
            return None

        if not validate or not self.sanitize:
            return value

        sanitize_vals = {
            'silent': True,
            'sanitize_tags': self.sanitize_tags,
            'sanitize_attributes': self.sanitize_attributes,
            'sanitize_style': self.sanitize_style,
            'sanitize_form': self.sanitize_form,
            'sanitize_conditional_comments': self.sanitize_conditional_comments,
            'output_method': self.sanitize_output_method,
            'strip_style': self.strip_style,
            'strip_classes': self.strip_classes
        }

        if self.sanitize_overridable:
            if record.env.user.has_group('base.group_sanitize_override'):
                return value

            original_value = record[self.name]
            if original_value:
                # Note that sanitize also normalize
                original_value_sanitized = html_sanitize(original_value, **sanitize_vals)
                original_value_normalized = html_normalize(original_value)

                if (
                    not original_value_sanitized  # sanitizer could empty it
                    or original_value_normalized != original_value_sanitized
                ):
                    # The field contains element(s) that would be removed if
                    # sanitized. It means that someone who was part of a group
                    # allowing to bypass the sanitation saved that field
                    # previously.

                    diff = unified_diff(
                        original_value_sanitized.splitlines(),
                        original_value_normalized.splitlines(),
                    )

                    with_colors = isinstance(logging.getLogger().handlers[0].formatter, ColoredFormatter)
                    diff_str = f'The field ({record._description}, {self.string}) will not be editable:\n'
                    for line in list(diff)[2:]:
                        if with_colors:
                            color = {'-': RED, '+': GREEN}.get(line[:1], DEFAULT)
                            diff_str += COLOR_PATTERN % (30 + color, 40 + DEFAULT, line.rstrip() + "\n")
                        else:
                            diff_str += line.rstrip() + '\n'
                    _logger.info(diff_str)

                    raise UserError(record.env._(
                        "The field value you're saving (%(model)s %(field)s) includes content that is "
                        "restricted for security reasons. It is possible that someone "
                        "with higher privileges previously modified it, and you are therefore "
                        "not able to modify it yourself while preserving the content.",
                        model=record._description, field=self.string,
                    ))

        return html_sanitize(value, **sanitize_vals)

    def convert_to_record(self, value, record):
        r = super().convert_to_record(value, record)
        if isinstance(r, bytes):
            r = r.decode()
        return r and Markup(r)

    def convert_to_read(self, value, record, use_display_name=True):
        r = super().convert_to_read(value, record, use_display_name)
        if isinstance(r, bytes):
            r = r.decode()
        return r and Markup(r)

    def get_trans_terms(self, value):
        # ensure the translation terms are stringified, otherwise we can break the PO file
        return list(map(str, super().get_trans_terms(value)))

    escape = staticmethod(markup_escape)
    is_empty = staticmethod(is_html_empty)
    to_plaintext = staticmethod(html2plaintext)
    from_plaintext = staticmethod(plaintext2html)


class LangProxyDict(collections.abc.MutableMapping):
    """A view on a dict[id, dict[lang, value]] that maps id to value given a
    fixed language."""
    __slots__ = ('_cache', '_field', '_lang')

    def __init__(self, field: BaseString, cache: dict, lang: str):
        super().__init__()
        self._field = field
        self._cache = cache
        self._lang = lang

    def get(self, key, default=None):
        # just for performance
        vals = self._cache.get(key, SENTINEL)
        if vals is SENTINEL:
            return default
        if vals is None:
            return None
        if not (self._field.compute or (self._field.store and (key or key.origin))):
            # the field's value is neither computed, nor in database
            # (non-stored field or new record without origin), so fallback on
            # its 'en_US' value in cache
            return vals.get(self._lang, vals.get('en_US', default))
        return vals.get(self._lang, default)

    def __getitem__(self, key):
        vals = self._cache[key]
        if vals is None:
            return None
        if not (self._field.compute or (self._field.store and (key or key.origin))):
            # the field's value is neither computed, nor in database
            # (non-stored field or new record without origin), so fallback on
            # its 'en_US' value in cache
            return vals.get(self._lang, vals.get('en_US'))
        return vals[self._lang]

    def __setitem__(self, key, value):
        if value is None:
            self._cache[key] = None
            return
        vals = self._cache.get(key)
        if vals is None:
            # key is not in cache, or {key: None} is in cache
            self._cache[key] = vals = {self._lang: value}
        else:
            vals[self._lang] = value
        if not (self._field.compute or (self._field.store and (key or key.origin))):
            # the field's value is neither computed, nor in database
            # (non-stored field or new record without origin), so the cache
            # must contain the fallback 'en_US' value for other languages
            vals.setdefault('en_US', value)

    def __delitem__(self, key):
        vals = self._cache.get(key)
        if vals:
            vals.pop(self._lang, None)

    def __iter__(self):
        for key, vals in self._cache.items():
            if vals is None or self._lang in vals:
                yield key

    def __len__(self):
        return sum(1 for _ in self)

    def clear(self):
        for vals in self._cache.values():
            if vals:
                vals.pop(self._lang, None)

    def __repr__(self):
        return f"<LangProxyDict lang={self._lang!r} size={len(self._cache)} at {hex(id(self))}>"

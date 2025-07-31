from __future__ import annotations

import itertools
import logging
import typing
from collections import defaultdict
from difflib import get_close_matches, unified_diff
from hashlib import sha256
from operator import attrgetter

from markupsafe import Markup
from markupsafe import escape as markup_escape
from psycopg2.extras import Json as PsycopgJson

from odoo.exceptions import UserError
from odoo.netsvc import COLOR_PATTERN, DEFAULT, GREEN, RED, ColoredFormatter
from odoo.tools import SQL, html_normalize, html_sanitize, sql
from odoo.tools.misc import SENTINEL, Sentinel
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

    def _convert_db_column(self, model, column):
        # specialized implementation for converting from/to translated fields
        if self.translate or column['udt_name'] == 'jsonb':
            sql.convert_column_translatable(model._cr, model._table, self.name, self.column_type[1])
        else:
            sql.convert_column(model._cr, model._table, self.name, self.column_type[1])

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

    def convert_to_column_update(self, value, record):
        if self.translate:
            return PsycopgJson(value) if value else value
        return super().convert_to_column_update(value, record)

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
        if callable(self.translate) and record.env.context.get('edit_translations'):
            if not self.get_trans_terms(value):
                return value
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

    def get_translation_fallback_langs(self, env):
        lang = (env.lang or 'en_US') if self.translate is True else env._lang
        if lang == '_en_US':
            return '_en_US', 'en_US'
        if lang == 'en_US':
            return ('en_US',)
        if lang.startswith('_'):
            return lang, lang[1:], '_en_US', 'en_US'
        return lang, 'en_US'

    def write(self, records, value):
        if not self.translate or value is False or value is None:
            super().write(records, value)
            return
        cache = records.env.cache
        cache_value = self.convert_to_cache(value, records)
        records = cache.get_records_different_from(records, self, cache_value)
        if not records:
            return

        # flush dirty None values
        dirty_records = cache.filtered_dirty_records(records, self)
        if any(v is None for v in cache.get_values(dirty_records, self)):
            dirty_records.flush_recordset([self.name])

        dirty = self.store and any(records._ids)
        lang = (records.env.lang or 'en_US') if self.translate is True else records.env._lang

        # not dirty fields
        if not dirty:
            if self.compute and self.inverse:
                # invalidate the values in other languages to force their recomputation
                values = [{lang: cache_value} for _id in records._ids]
                cache.update_raw(records, self, values, dirty=False)
            else:
                cache.update(records, self, itertools.repeat(cache_value), dirty=False)
            return

        # model translation
        if not callable(self.translate):
            # invalidate clean fields because them may contain fallback value
            clean_records = cache.filtered_clean_records(records, self)
            clean_records.invalidate_recordset([self.name])
            cache.update(records, self, itertools.repeat(cache_value), dirty=True)
            if lang != 'en_US' and not records.env['res.lang']._get_data(code='en_US'):
                # if 'en_US' is not active, we always write en_US to make sure value_en is meaningful
                cache.update(records.with_context(lang='en_US'), self, itertools.repeat(cache_value), dirty=True)
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
        # Maybe we can use Cache.update(records.with_context(cache_update_raw=True), self, new_translations_list, dirty=True)
        cache.update_raw(records, self, new_translations_list, dirty=True)

    def to_sql(self, model: BaseModel, alias: str, flush: bool = True) -> SQL:
        sql_field = super().to_sql(model, alias, flush)
        if self.translate:
            langs = self.get_translation_fallback_langs(model.env)
            sql_field_langs = [SQL("%s->>%s", sql_field, lang) for lang in langs]
            if len(sql_field_langs) == 1:
                return sql_field_langs[0]
            return SQL("COALESCE(%s)", SQL(", ").join(sql_field_langs))
        return sql_field

    def to_raw_sql(self, model: BaseModel, alias: str, flush: bool = True) -> SQL:
        """Return the `SQL` object that accesses directly the field.  In the
        case of translated fields, this returns the ``jsonb`` dictionary as a whole.
        """
        return Field.to_sql(self, model, alias, flush)

    def condition_to_sql(self, field_expr: str, operator: str, value, model: BaseModel, alias: str, query: Query) -> SQL:
        # build the condition
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

            raw_sql_field = self.to_raw_sql(model, alias)
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
        ``True``). Note that the trim operation is applied only by the web client.

    :param translate: enable the translation of the field's values; use
        ``translate=True`` to translate field values as a whole; ``translate``
        may also be a callable such that ``translate(callback, value)``
        translates ``value`` by using ``callback(term)`` to retrieve the
        translation of terms.
    :type translate: bool or callable
    """
    type = 'char'
    trim: bool = True                   # whether value is trimmed (only by web client)

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
            sql.convert_column(model._cr, model._table, self.name, self.column_type[1])
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

import logging
import typing
from collections import defaultdict
from typing import Self

from odoo.libs.debug_log import DebugLog

from ..._typing import ValuesType
from ...primitives import MAGIC_COLUMNS, Command
from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection

    from ..._typing import BaseModel

_logger = logging.getLogger("odoo.models")
_debug = DebugLog(__name__)


class CopyMixin(_ModelStubs):
    __slots__ = ()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType | None]:
        if len(set(self._ids)) != len(self._ids):
            raise ValueError(
                f"Cannot copy {self._name} records: the same record appears "
                f"more than once in {self}. Deduplicate the recordset first "
                f"(e.g. `records.browse(unique(records._ids))`); copying it "
                f"twice over would yield a single copy."
            )

        vals_list: list[dict | None] = []
        default = dict(default or {})
        if "__copy_data_seen" not in self.env.context:
            self = self.with_context(__copy_data_seen=defaultdict(set))

        blacklist = set(MAGIC_COLUMNS + ["parent_path"])
        whitelist = {
            name for name, field in self._fields.items() if not field.inherited
        }

        def blacklist_given_fields(model):
            for parent_model, parent_field in model._inherits.items():
                blacklist.add(parent_field)
                if parent_field in default:
                    blacklist.update(set(self.env[parent_model]._fields) - whitelist)
                else:
                    blacklist_given_fields(self.env[parent_model])

        blacklist_given_fields(self)

        fields_to_copy = {
            name: field
            for name, field in self._fields.items()
            if field.copy
            and name not in default
            and name not in blacklist
            and self._has_field_access(field, "read")
        }

        # the records a batch may link through its many2many fields, filtered
        # once per field: each record then keeps the ones it holds
        readable_by_field = {
            name: set(self[name]._filtered_access("read")._ids)
            for name, field in fields_to_copy.items()
            if field.is_many2many
        }

        seen_map = self.env.context["__copy_data_seen"]
        _debug.pipeline(
            "copy.data",
            model=self._name,
            records=len(self),
            fields=len(fields_to_copy),
            blacklisted=len(blacklist),
            defaults=len(default),
        )

        for record in self:
            if record.id in seen_map[record._name]:
                _debug.logic(
                    "copy.data_seen_skipped", model=self._name, record=record.id
                )
                vals_list.append(None)
                continue
            seen_map[record._name].add(record.id)

            vals = default.copy()

            for name, field in fields_to_copy.items():
                if field.is_one2many:
                    lines = record[name].sorted(key="id")
                    lines = lines.filtered(
                        lambda line: line.id not in seen_map[line._name]
                    ).with_prefetch(lines._prefetch_ids)
                    vals[name] = [
                        Command.create(line) for line in lines.copy_data() if line
                    ]
                elif field.is_many2many:
                    readable = readable_by_field[name]
                    vals[name] = [
                        Command.set(
                            [id_ for id_ in record[name]._ids if id_ in readable]
                        )
                    ]
                else:
                    vals[name] = field.convert_to_write(record[name], record)
            vals_list.append(vals)
        return vals_list

    def copy_translations(self, new: Self, excluded: Collection[str] = ()) -> None:
        # Materialised once: callers pass generators, which a membership test per
        # field would consume, and the trace below takes its length.
        excluded = frozenset(excluded)
        old = self
        if "__copy_translations_seen" not in old.env.context:
            old = old.with_context(__copy_translations_seen=defaultdict(set))
        seen_map = old.env.context["__copy_translations_seen"]
        if old.id in seen_map[old._name]:
            _debug.logic(
                "copy.translations_seen_skipped", model=old._name, record=old.id
            )
            return
        seen_map[old._name].add(old.id)
        valid_langs = {*self.env.registry.locale.installed_langs(self.env), "en_US"}

        for name, field in old._fields.items():
            if not field.copy:
                continue

            if (
                field.inherited
                and field.related is not None
                and field.related.split(".")[0] in excluded
            ):
                continue

            if field.is_one2many and field.name not in excluded:
                old_lines = old[name].sorted(key="id")
                new_lines = new[name].sorted(key="id")
                if len(old_lines) != len(new_lines):
                    _logger.debug(
                        "copy_translations: skipping one2many field %r on %s: "
                        "%d source line(s) but %d copied line(s) "
                        "(copy_data recursion guard dropped lines)",
                        name,
                        old._name,
                        len(old_lines),
                        len(new_lines),
                    )
                    _debug.logic(
                        "copy.translations_o2m_mismatch",
                        model=old._name,
                        field=name,
                        source_lines=len(old_lines),
                        copied_lines=len(new_lines),
                    )
                    continue
                for old_line, new_line in zip(old_lines, new_lines, strict=True):
                    old_line.copy_translations(new_line)

            elif field.translate and field.store and name not in excluded and old[name]:
                old._copy_field_translations(new, name, field, valid_langs)
        _debug.pipeline(
            "copy.translations",
            model=old._name,
            record=old.id,
            target=new.id,
            excluded=len(excluded),
            langs=len(valid_langs),
        )

    def _copy_field_translations(
        self, new: Self, name: str, field, valid_langs: set[str]
    ) -> None:
        old_stored_translations = field._get_stored_translations(
            typing.cast("BaseModel", self)
        )
        if not old_stored_translations:
            return
        lang = self.env.lang or "en_US"
        if field.translate is True:
            translations: dict = {
                k: v
                for k, v in old_stored_translations.items()
                if k in valid_langs and k != lang
            }
        else:
            old_translations = {
                k: old_stored_translations.get(f"_{k}", v)
                for k, v in old_stored_translations.items()
                if k in valid_langs
            }
            source_term = old_translations.pop(lang, None)
            if source_term is None:
                source_term = old_translations.get("en_US")
            if source_term is None:
                _debug.logic(
                    "copy.field_translations_no_source",
                    model=self._name,
                    field=name,
                    record=self.id,
                    lang=lang,
                )
                return
            translation_dictionary = field.get_translation_dictionary(
                source_term,
                old_translations,
            )
            translations = defaultdict(dict)
            for from_lang_term, to_lang_terms in translation_dictionary.items():
                for term_lang, to_lang_term in to_lang_terms.items():
                    translations[term_lang][from_lang_term] = to_lang_term
        _debug.logic(
            "copy.field_translations",
            model=self._name,
            field=name,
            record=self.id,
            target=new.id,
            terms=field.translate is not True,
            langs=len(translations),
        )
        new.update_field_translations(name, translations)

    def _copy_translations_of_renamed_field(
        self,
        new: Self,
        field_name: str,
        rename: Callable[[Self, str], str],
    ) -> None:
        field = self._fields[field_name]
        assert field.translate is True and field.store, (
            f"{field} is not a stored translate=True field"
        )
        if new[field_name] != rename(self, self[field_name]):
            return
        stored_translations = field._get_stored_translations(
            typing.cast("BaseModel", self)
        )
        if not stored_translations:
            return
        valid_langs = {*self.env.registry.locale.installed_langs(self.env), "en_US"}
        renamed = {
            lang: rename(self.with_context(lang=lang), term)
            for lang, term in stored_translations.items()
            if lang in valid_langs
        }
        _debug.logic(
            "copy.renamed_field_translations",
            model=self._name,
            field=field_name,
            record=self.id,
            target=new.id,
            langs=len(renamed),
        )
        field._update_cache(new, renamed, dirty=True)

    def copy(self, default: ValuesType | None = None) -> Self:
        vals_list = self.with_context(active_test=False).copy_data(default)
        pairs = [
            (rec, vals)
            for rec, vals in zip(self, vals_list, strict=True)
            if vals is not None
        ]
        _debug.pipeline(
            "copy.records",
            model=self._name,
            records=len(self),
            copyable=len(pairs),
            default_keys=len(default or ()),
        )
        if not pairs:
            return self.browse()
        new_records = self.create([vals for _, vals in pairs])
        _debug.lifecycle(
            "copy.records_created",
            model=self._name,
            sources=len(pairs),
            created=len(new_records),
        )
        for (old_record, _), new_record in zip(pairs, new_records, strict=True):
            old_record.copy_translations(new_record, excluded=default or ())
        return new_records

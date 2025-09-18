"""
Copy (duplication) mixin for BaseModel.

Extracted from crud.py — contains the copy, copy_data, and copy_translations
methods that handle record duplication with proper field and translation handling.
"""

import typing
from collections import defaultdict
from collections.abc import Collection
from typing import Self

from ..._typing import ValuesType
from ...primitives import MAGIC_COLUMNS, Command


class CopyMixin:
    """Mixin providing record duplication operations.

    Methods:
    - copy_data(): Copy record field values, respecting copy=True flags
    - copy_translations(): Recursively copy field translations
    - copy(): Main entry point — duplicate records with optional defaults
    """

    __slots__ = ()

    def copy_data(self, default: ValuesType | None = None) -> list[ValuesType]:
        """
        Copy given record's data with all its fields values

        :param default: field values to override in the original values of the copied record
        :return: list of dictionaries containing all the field values
        """
        vals_list = []
        default = dict(default or {})
        # avoid recursion through already copied records in case of circular relationship
        if "__copy_data_seen" not in self.env.context:
            self = self.with_context(__copy_data_seen=defaultdict(set))

        # build a black list of fields that should not be copied
        blacklist = set(MAGIC_COLUMNS + ["parent_path"])
        whitelist = {
            name for name, field in self._fields.items() if not field.inherited
        }

        def blacklist_given_fields(model):
            # blacklist the fields that are given by inheritance
            for parent_model, parent_field in model._inherits.items():
                blacklist.add(parent_field)
                if parent_field in default:
                    # all the fields of 'parent_model' are given by the record:
                    # default[parent_field], except the ones redefined in self
                    blacklist.update(set(self.env[parent_model]._fields) - whitelist)
                else:
                    blacklist_given_fields(self.env[parent_model])

        blacklist_given_fields(self)

        fields_to_copy = {
            name: field
            for name, field in self._fields.items()
            if field.copy and name not in default and name not in blacklist
        }

        for record in self:
            seen_map = self.env.context["__copy_data_seen"]
            if record.id in seen_map[record._name]:
                vals_list.append(None)
                continue
            seen_map[record._name].add(record.id)

            vals = default.copy()

            for name, field in fields_to_copy.items():
                if field.type == "one2many":
                    # duplicate following the order of the ids because we'll rely on
                    # it later for copying translations in copy_translation()!
                    lines = record[name].sorted(key="id").copy_data()
                    # the lines are duplicated using the wrong (old) parent, but then are
                    # reassigned to the correct one thanks to the (Command.CREATE, 0, ...)
                    vals[name] = [Command.create(line) for line in lines if line]
                elif field.type == "many2many":
                    # copy only links that we can read, otherwise the write will fail
                    vals[name] = [
                        Command.set(record[name]._filtered_access("read").ids)
                    ]
                else:
                    vals[name] = field.convert_to_write(record[name], record)
            vals_list.append(vals)
        return vals_list

    def copy_translations(self, new: Self, excluded: Collection[str] = ()) -> None:
        """Recursively copy the translations from original to new record

        :param self: the original record
        :param new: the new record (copy of the original one)
        :param excluded: a container of user-provided field names
        """
        old = self
        # avoid recursion through already copied records in case of circular relationship
        if "__copy_translations_seen" not in old.env.context:
            old = old.with_context(__copy_translations_seen=defaultdict(set))
        seen_map = old.env.context["__copy_translations_seen"]
        if old.id in seen_map[old._name]:
            return
        seen_map[old._name].add(old.id)
        valid_langs = {code for code, _ in self.env["res.lang"].get_installed()} | {
            "en_US"
        }

        for name, field in old._fields.items():
            if not field.copy:
                continue

            if field.inherited and field.related.split(".")[0] in excluded:
                # inherited fields that come from a user-provided parent record
                # must not copy translations, as the parent record is not a copy
                # of the old parent record
                continue

            if field.type == "one2many" and field.name not in excluded:
                # we must recursively copy the translations for o2m; here we
                # rely on the order of the ids to match the translations as
                # foreseen in copy_data()
                old_lines = old[name].sorted(key="id")
                new_lines = new[name].sorted(key="id")
                for old_line, new_line in zip(old_lines, new_lines, strict=False):
                    # don't pass excluded as it is not about those lines
                    old_line.copy_translations(new_line)

            elif field.translate and field.store and name not in excluded and old[name]:
                # for translatable fields we copy their translations
                old_stored_translations = field._get_stored_translations(old)
                if not old_stored_translations:
                    continue
                lang = self.env.lang or "en_US"
                if field.translate is True:
                    new.update_field_translations(
                        name,
                        {
                            k: v
                            for k, v in old_stored_translations.items()
                            if k in valid_langs and k != lang
                        },
                    )
                else:
                    old_translations = {
                        k: old_stored_translations.get(f"_{k}", v)
                        for k, v in old_stored_translations.items()
                        if k in valid_langs
                    }
                    # {from_lang_term: {lang: to_lang_term}
                    translation_dictionary = field.get_translation_dictionary(
                        old_translations.pop(lang, old_translations["en_US"]),
                        old_translations,
                    )
                    # {lang: {old_term: new_term}}
                    translations = defaultdict(dict)
                    for (
                        from_lang_term,
                        to_lang_terms,
                    ) in translation_dictionary.items():
                        for lang, to_lang_term in to_lang_terms.items():
                            translations[lang][from_lang_term] = to_lang_term
                    new.update_field_translations(name, translations)

    def copy(self, default: ValuesType | None = None) -> Self:
        """Duplicate record ``self`` updating it with default values.

        :param default: dictionary of field values to override in the
               original values of the copied record, e.g: ``{'field_name': overridden_value, ...}``
        :returns: new records

        """
        vals_list = self.with_context(active_test=False).copy_data(default)
        new_records = self.create(vals_list)
        for old_record, new_record in zip(self, new_records, strict=False):
            old_record.copy_translations(new_record, excluded=default or ())
        return new_records

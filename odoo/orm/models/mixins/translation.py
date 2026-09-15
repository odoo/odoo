import typing

from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools.translate import _

from ._model_stubs import _ModelStubs

if typing.TYPE_CHECKING:
    from collections.abc import Callable, Collection

_debug = DebugLog(__name__)


class TranslationMixin(_ModelStubs):
    __slots__ = ()

    def update_field_translations(
        self,
        field_name: str,
        translations: dict[str, str | typing.Literal[False] | dict[str, str]],
        source_lang: str = "",
    ) -> bool:
        return self._update_field_translations(
            field_name, translations, source_lang=source_lang
        )

    def _check_translation_langs(self, translations: dict, source_lang: str) -> None:
        valid_langs = {*self.env.registry.locale.installed_langs(self.env), "en_US"}
        missing_langs = (set(translations) | {source_lang}) - valid_langs
        if missing_langs:
            _debug.logic(
                "translation.langs_inactive",
                model=self._name,
                missing=sorted(missing_langs),
                installed=len(valid_langs),
            )
            raise UserError(
                _(
                    "The following languages are not activated: %(missing_names)s",
                    missing_names=", ".join(missing_langs),
                )
            )

    def _update_model_translations(self, field_name: str, translations: dict) -> bool:
        if any(
            translation and not isinstance(translation, str)
            for translation in translations.values()
        ):
            raise UserError(
                _(
                    "Translations for model translated fields only accept falsy values and str"
                )
            )
        value_en = translations.get("en_US", True)
        if not value_en and value_en != "":
            translations.pop("en_US")
        translations = {
            lang: translation if isinstance(translation, str) else None
            for lang, translation in translations.items()
        }
        if not translations:
            _debug.logic(
                "translation.model_update_empty", model=self._name, field=field_name
            )
            return False

        translation_fallback = (
            translations["en_US"]
            if translations.get("en_US") is not None
            else (
                translations[self.env.lang]
                if translations.get(self.env.lang) is not None
                else next(
                    (v for v in translations.values() if v is not None),
                    None,
                )
            )
        )
        self.invalidate_recordset([field_name])
        rows = self.env.backend.columns.merge_json(
            self, field_name, self.id, {"en_US": translation_fallback}, translations
        )
        _debug.lifecycle(
            "translation.model_updated",
            model=self._name,
            field=field_name,
            record=self.id,
            langs=len(translations),
            fallback=translation_fallback is not None,
            rows=rows,
        )
        self.modified([field_name])
        return True

    def _update_term_translations(
        self, field, translations: dict, digest, source_lang: str
    ) -> bool:
        old_values = field._get_stored_translations(self)
        if not old_values:
            _debug.logic(
                "translation.terms_no_stored_values",
                model=self._name,
                field=field.name,
                record=self.id,
            )
            return False

        for lang in translations:
            if f"_{lang}" in old_values:
                old_values[lang] = old_values.pop(f"_{lang}")
        translations = {
            lang: _translations
            for lang, _translations in translations.items()
            if _translations
        }

        source_key = next(
            (
                lang
                for lang in [
                    f"_{source_lang}",
                    source_lang,
                    "_en_US",
                    "en_US",
                ]
                if lang in old_values
            ),
            None,
        )
        if source_key is not None:
            old_source_lang_value = old_values[source_key]
        else:
            old_source_lang_value = next(iter(old_values.values()))
        old_values_to_translate = {
            lang: value
            for lang, value in old_values.items()
            if lang != source_lang and lang in translations
        }
        old_translation_dictionary = field.get_translation_dictionary(
            old_source_lang_value, old_values_to_translate
        )

        if digest:
            digested2term = {
                digest(old_en_term): old_en_term
                for old_en_term in old_translation_dictionary
            }
            translations = {
                lang: {
                    digested2term[src]: value
                    for src, value in lang_translations.items()
                    if src in digested2term
                }
                for lang, lang_translations in translations.items()
            }

        new_values = old_values
        for lang, _translations in translations.items():
            _old_translations = {
                src: values[lang]
                for src, values in old_translation_dictionary.items()
                if lang in values
            }
            _new_translations = _old_translations | _translations
            new_values[lang] = field.convert_to_cache(
                field.translate(_new_translations.get, old_source_lang_value),
                self,
            )
        _debug.pipeline(
            "translation.terms_updated",
            model=self._name,
            field=field.name,
            record=self.id,
            langs=len(translations),
            terms=len(old_translation_dictionary),
            digest=digest is not None,
            source_key=source_key,
        )
        field._update_cache(
            self.with_context(prefetch_langs=True), new_values, dirty=True
        )
        return True

    def _update_field_translations(
        self,
        field_name: str,
        translations: dict[str, str | typing.Literal[False] | dict[str, str]],
        digest: Callable[[str], str] | None = None,
        source_lang: str = "",
    ) -> bool:
        self.check_singleton()

        self.check_access("write")
        field = self._fields[field_name]
        translations = dict(translations)
        self._check_field_access(field, "write")
        source_lang = source_lang or "en_US"
        self._check_translation_langs(translations, source_lang)

        if not field.translate:
            _debug.logic(
                "translation.update_skipped",
                model=self._name,
                field=field_name,
                reason="not_translated",
            )
            return False

        if not field.store and not field.related and field.compute:
            _debug.logic(
                "translation.update_skipped",
                model=self._name,
                field=field_name,
                reason="computed_unstored",
            )
            return False

        if field.related and not field.store:
            related_path, field_name = field.related.rsplit(".", 1)
            _debug.logic(
                "translation.update_delegated",
                model=self._name,
                field=field.name,
                related=field.related,
            )
            return self.mapped(related_path)._update_field_translations(
                field_name, translations, digest, source_lang=source_lang
            )
        _debug.pipeline(
            "translation.update",
            model=self._name,
            field=field_name,
            langs=len(translations),
            source_lang=source_lang,
            mode="model" if field.translate is True else "terms",
        )

        if field.translate is True:
            if not self._update_model_translations(field_name, translations):
                return False
        elif not self._update_term_translations(
            field, translations, digest, source_lang
        ):
            return False

        self[field_name] = self[field_name]
        return True

    def get_field_translations(
        self, field_name: str, langs: Collection[str] | None = None
    ) -> tuple[list[dict[str, str]], dict[str, typing.Any]]:
        self.check_singleton()
        field = self._fields[field_name]
        langs = set(langs or self.env.registry.locale.installed_langs(self.env))
        self_lang = self.with_context(check_translations=True, prefetch_langs=True)
        val_en = self_lang.with_context(lang="en_US")[field_name]
        if not field.translate:
            translations = []
        elif field.translate is True:
            translations = [
                {
                    "lang": lang,
                    "source": val_en,
                    "value": self_lang.with_context(lang=lang)[field_name],
                }
                for lang in langs
            ]
        else:
            translation_dictionary = field.get_translation_dictionary(
                val_en,
                {lang: self_lang.with_context(lang=lang)[field_name] for lang in langs},
            )
            translations = [
                {
                    "lang": lang,
                    "source": term_en,
                    "value": term_lang if term_lang != term_en else "",
                }
                for term_en, translations in translation_dictionary.items()
                for lang, term_lang in translations.items()
            ]
        context: dict[str, typing.Any] = {}
        context["translation_type"] = (
            "text" if field.type in ["text", "html"] else "char"
        )
        context["translation_show_source"] = callable(field.translate)

        _debug.perf.count(
            "translation.field_translations_read",
            model=self._name,
            field=field_name,
            record=self.id,
            langs=len(langs),
            entries=len(translations),
            terms=callable(field.translate),
        )
        return translations, context

    def _get_base_lang(self) -> str:
        self.check_singleton()
        return "en_US"

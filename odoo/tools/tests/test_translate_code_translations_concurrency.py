import unittest
from unittest.mock import patch

from odoo.tools.translate import CodeTranslations


class _ClearedRightAfterStore(dict):
    def __setitem__(self, key, value):
        pass


class _KeyInsertingOnRead(tuple):
    __slots__ = ()
    cache: dict | None = None

    def __getitem__(self, index):
        cache, type(self).cache = type(self).cache, None
        if cache is not None:
            cache[("inserted", "fr_FR")] = {}
        return super().__getitem__(index)


def _loaded(module_name, lang, filter_func):
    return {"src": f"{module_name}:{lang}"}


@patch.object(CodeTranslations, "_get_code_translations", staticmethod(_loaded))
class TestCodeTranslationsConcurrentClear(unittest.TestCase):
    def test_python_get_survives_a_clear_between_store_and_read(self):
        translations = CodeTranslations()
        translations.python_translations = _ClearedRightAfterStore()
        result = translations.get_python_translations("mod", "fr_FR")
        self.assertEqual(dict(result), {"src": "mod:fr_FR"})

    def test_web_get_survives_a_clear_between_store_and_read(self):
        translations = CodeTranslations()
        translations.web_translations = _ClearedRightAfterStore()
        result = translations.get_web_translations("mod", "fr_FR")
        self.assertEqual(
            [dict(message) for message in result["messages"]],
            [{"id": "src", "string": "mod:fr_FR"}],
        )

    def test_get_caches_the_loaded_mapping(self):
        translations = CodeTranslations()
        first = translations.get_python_translations("mod", "fr_FR")
        self.assertIs(translations.get_python_translations("mod", "fr_FR"), first)
        self.assertIs(translations.python_translations[("mod", "fr_FR")], first)

    def test_module_clear_survives_an_insert_while_it_filters(self):
        translations = CodeTranslations()
        cache = translations.python_translations
        cache[_KeyInsertingOnRead(("mod", "fr_FR"))] = {}
        cache[("other", "fr_FR")] = {}
        _KeyInsertingOnRead.cache = cache
        translations.clear("mod")
        self.assertEqual(set(cache), {("other", "fr_FR"), ("inserted", "fr_FR")})


if __name__ == "__main__":
    unittest.main()

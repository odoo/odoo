import inspect

from odoo.orm.runtime.registry import Registry
from odoo.tools.translate import code_translations


def test_a_rebuild_drops_the_code_translations_before_loading_modules():
    """The cache is process-global and `_load_module_terms` clears it only
    in the worker that upgrades; every other worker learns of the change by
    rebuilding its registry. Building a real registry inside a test runs the
    module's tests inside the test (b2ec8e8bb6e5's pin did), so the seam is
    read from the source, as the savepoint seam is."""
    src = inspect.getsource(Registry.new)
    assert "code_translations.clear()" in src
    assert src.index("code_translations.clear()") < src.index("load_modules(")


def test_clear_empties_both_caches():
    code_translations.web_translations[("probe", "fr_FR")] = {"messages": ()}
    code_translations.python_translations[("probe", "fr_FR")] = {"a": "b"}
    code_translations.clear()
    assert ("probe", "fr_FR") not in code_translations.web_translations
    assert ("probe", "fr_FR") not in code_translations.python_translations

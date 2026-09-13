import pytest

from odoo import fields, models
from odoo.exceptions import UserError
from odoo.orm.model_test_env import model_test_env

_MOD = "test_translations_dbfree"


class Doc(models.Model):
    _name = "trd.doc"
    _module = _MOD
    _description = "a model-translated title"
    _log_access = False

    title = fields.Char(translate=True)
    body = fields.Html(translate=True)


@pytest.fixture
def env():
    with model_test_env(Doc, langs=("fr_FR",)) as env:
        yield env


def _stored(env, doc):
    return env.cr.storage.get_row("trd_doc", doc.id)["title"]


def test_the_installed_languages_come_from_the_harness(env):
    assert env.registry.locale.installed_langs(env) == ["en_US", "fr_FR"]
    assert env["trd.doc"].with_context(lang="fr_FR").env.lang == "fr_FR"
    with pytest.raises(UserError, match="Invalid language code"):
        env["trd.doc"].with_context(lang="de_DE").env.lang


def test_a_write_in_a_language_keeps_the_others(env):
    doc = env["trd.doc"].create({"title": "Hello"})
    doc.with_context(lang="fr_FR").title = "Bonjour"
    env.flush_all()
    assert _stored(env, doc) == {"en_US": "Hello", "fr_FR": "Bonjour"}
    assert doc.title == "Hello"
    assert doc.with_context(lang="fr_FR").title == "Bonjour"


def test_update_field_translations_merges_into_the_stored_object(env):
    doc = env["trd.doc"].create({"title": "Hello"})
    env.flush_all()
    assert doc.update_field_translations("title", {"fr_FR": "Salut"})
    assert _stored(env, doc) == {"en_US": "Hello", "fr_FR": "Salut"}
    assert doc.with_context(lang="fr_FR").title == "Salut"
    # a false value deletes the language, the fallback keeps en_US alive
    assert doc.update_field_translations("title", {"fr_FR": False})
    assert _stored(env, doc) == {"en_US": "Hello"}
    with pytest.raises(UserError, match="not activated"):
        doc.update_field_translations("title", {"de_DE": "Hallo"})


def test_copy_carries_the_translations(env):
    doc = env["trd.doc"].create({"title": "Hello"})
    doc.with_context(lang="fr_FR").title = "Bonjour"
    copy = doc.copy()
    assert _stored(env, copy) == {"en_US": "Hello", "fr_FR": "Bonjour"}
    assert copy.with_context(lang="fr_FR").title == "Bonjour"


def test_a_search_in_a_language_reads_that_language(env):
    doc = env["trd.doc"].create({"title": "Hello"})
    doc.with_context(lang="fr_FR").title = "Bonjour"
    Doc = env["trd.doc"]
    assert Doc.with_context(lang="fr_FR").search([("title", "ilike", "bonj")]) == doc
    assert not Doc.search([("title", "ilike", "bonj")])
    assert Doc.search([("title", "=", "Hello")]) == doc


def test_get_field_translations_reads_every_language_of_the_stored_object(env):
    doc = env["trd.doc"].create({"title": "Hello"})
    doc.with_context(lang="fr_FR").title = "Bonjour"
    env.flush_all()
    env.invalidate_all()
    translations, context = doc.get_field_translations("title")
    assert sorted(translations, key=lambda t: t["lang"]) == [
        {"lang": "en_US", "source": "Hello", "value": "Hello"},
        {"lang": "fr_FR", "source": "Hello", "value": "Bonjour"},
    ]
    assert context == {"translation_type": "char", "translation_show_source": False}
    # a read of the whole object under prefetch_langs leaves the plain reads intact
    assert doc.with_context(lang="fr_FR").title == "Bonjour"
    assert doc.title == "Hello"


def test_a_term_translated_html_answers_its_terms(env):
    doc = env["trd.doc"].create({"body": "<p>Hello</p><p>World</p>"})
    env.flush_all()
    assert doc.update_field_translations("body", {"fr_FR": {"Hello": "Bonjour"}})
    assert doc.with_context(lang="fr_FR").body == "<p>Bonjour</p><p>World</p>"
    assert doc.body == "<p>Hello</p><p>World</p>"
    translations, context = doc.get_field_translations("body", ["fr_FR"])
    assert {t["source"]: t["value"] for t in translations} == {
        "Hello": "Bonjour",
        "World": "",
    }
    assert context["translation_show_source"] is True

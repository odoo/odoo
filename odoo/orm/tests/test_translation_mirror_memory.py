from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_translation_mirror_memory"


class ResLang(models.AbstractModel):
    _name = "res.lang"
    _module = _MOD
    _description = "res.lang (test stub)"

    def get_installed(self):
        return [("en_US", "English (US)"), ("fr_FR", "French")]

    def _get_data(self, **kwargs):
        return kwargs.get("code") in ("en_US", "fr_FR")


class Label(models.Model):
    _name = "tmm.label"
    _module = _MOD
    _description = "label"
    _log_access = False

    name = fields.Char(translate=True)


def test_a_write_in_one_language_follows_into_the_languages_that_echoed_it():
    with model_test_env(ResLang, Label) as env:
        echoed = env["tmm.label"].create({"name": "Hello"})
        translated = env["tmm.label"].create({"name": "Hello"})
        translated.with_context(lang="fr_FR").name = "Bonjour"
        env.flush_all()

        (echoed + translated).name = "Hi"
        env.flush_all()
        env.invalidate_all()

        assert echoed.with_context(lang="fr_FR").name == "Hi"
        assert translated.with_context(lang="fr_FR").name == "Bonjour"
        assert translated.name == "Hi"

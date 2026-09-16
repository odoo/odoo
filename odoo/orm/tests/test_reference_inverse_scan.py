from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_MOD = "test_reference_inverse_scan"


class Note(models.Model):
    _name = "ris.note"
    _module = _MOD
    _description = "note"
    _log_access = False

    body = fields.Char()
    res_model = fields.Char()
    res_id = fields.Many2oneReference(model_field="res_model")


class Alpha(models.Model):
    _name = "ris.alpha"
    _module = _MOD
    _description = "alpha"
    _log_access = False

    name = fields.Char()
    note_ids = fields.One2many(
        "ris.note", "res_id", domain=[("res_model", "=", "ris.alpha")]
    )
    important_note_ids = fields.One2many(
        "ris.note",
        "res_id",
        domain=[("res_model", "=", "ris.alpha"), ("body", "=", "important")],
    )


class Beta(models.Model):
    _name = "ris.beta"
    _module = _MOD
    _description = "beta"
    _log_access = False

    name = fields.Char()
    note_ids = fields.One2many(
        "ris.note", "res_id", domain=[("res_model", "=", "ris.beta")]
    )


def _env():
    return model_test_env(Note, Alpha, Beta)


def test_reference_field_has_one_inverse_per_pointing_model():
    with _env() as env:
        inverses = env.registry.field_inverses[env["ris.note"]._fields["res_id"]]
        assert {inv.model_name for inv in inverses} == {"ris.alpha", "ris.beta"}


def test_inverse_cache_is_populated_for_the_referenced_model():
    with _env() as env:
        alpha = env["ris.alpha"].create({"name": "a"})
        note = env["ris.note"].create(
            {"body": "n", "res_model": "ris.alpha", "res_id": alpha.id}
        )

        assert alpha.note_ids.ids == note.ids


def test_other_models_inverse_is_left_untouched():
    with _env() as env:
        alpha = env["ris.alpha"].create({"name": "a"})
        beta = env["ris.beta"].create({"name": "b"})
        beta_field = env["ris.beta"]._fields["note_ids"]
        beta_cache = beta_field._get_cache(env)
        beta_cache.pop(beta.id, None)

        env["ris.note"].create(
            {"body": "n", "res_model": "ris.alpha", "res_id": alpha.id}
        )

        assert beta.id not in beta_cache


def test_a_batch_naming_two_models_updates_both():
    with _env() as env:
        alpha = env["ris.alpha"].create({"name": "a"})
        beta = env["ris.beta"].create({"name": "b"})

        notes = env["ris.note"].create(
            [
                {"body": "na", "res_model": "ris.alpha", "res_id": alpha.id},
                {"body": "nb", "res_model": "ris.beta", "res_id": beta.id},
            ]
        )

        assert alpha.note_ids.ids == notes[0].ids
        assert beta.note_ids.ids == notes[1].ids


def _pointing_model(index):
    return type(
        f"Pointer{index}",
        (models.Model,),
        {
            "_name": f"ris.pointer{index}",
            "_module": _MOD,
            "_description": "pointer",
            "_log_access": False,
            "name": fields.Char(),
            "note_ids": fields.One2many(
                "ris.note",
                "res_id",
                domain=[("res_model", "=", f"ris.pointer{index}")],
            ),
        },
    )


def _browses_for_one_reference(extra_models):
    classes = [Note, Alpha, Beta, *(_pointing_model(i) for i in range(extra_models))]
    with model_test_env(*classes) as env:
        alpha = env["ris.alpha"].create({"name": "a"})
        note = env["ris.note"].create(
            {"body": "n", "res_model": "ris.alpha", "res_id": alpha.id}
        )
        field = env["ris.note"]._fields["res_id"]
        inverses = len(env.registry.field_inverses[field])

        calls = []
        note_cls = type(env["ris.note"])
        original = note_cls.browse
        note_cls.browse = lambda self, ids=(): (  # type: ignore[func-returns-value]
            calls.append(1),  # type: ignore[func-returns-value]
            original(self, ids),
        )[1]
        try:
            field._update_inverses([(note, alpha.id)])
        finally:
            note_cls.browse = original
        return inverses, len(calls)


def test_browsing_does_not_grow_with_the_number_of_inverse_fields():
    few_inverses, few_browses = _browses_for_one_reference(0)
    many_inverses, many_browses = _browses_for_one_reference(12)

    assert many_inverses == few_inverses + 12
    assert many_browses == few_browses


def test_reference_to_an_unknown_model_updates_nothing():
    with _env() as env:
        alpha = env["ris.alpha"].create({"name": "a"})

        env["ris.note"].create(
            {"body": "n", "res_model": "ris.nowhere", "res_id": alpha.id}
        )

        assert alpha.note_ids.ids == []

import pytest

from odoo import fields, models
from odoo.orm.model_test_env import model_test_env

_BASE = "test_selection_add_dbfree_base"
_EXT = "test_selection_add_dbfree_ext"


class Doc(models.Model):
    _name = "sela.doc"
    _module = _BASE
    _description = "a document with selections extended by another module"
    _log_access = False

    state = fields.Selection([("draft", "Draft"), ("done", "Done")], default="draft")
    kind = fields.Selection([("a", "A"), ("b", "B")], required=True, default="a")
    mode = fields.Selection(selection="_selection_mode")
    level = fields.Selection([("lo", "Lo")])

    def _selection_mode(self):
        return [("x", "X")]


class DocExtension(models.Model):
    _inherit = "sela.doc"
    _module = _EXT

    state = fields.Selection(
        selection_add=[("sent", "Sent"), ("done",), ("cancel", "Cancelled")],
        ondelete={"sent": "set default", "cancel": "cascade"},
    )
    kind = fields.Selection(selection_add=[("c", "C")], ondelete={"c": "set a"})


def test_selection_add_merges_in_order_with_its_ondelete_policies():
    with model_test_env(Doc, DocExtension) as env:
        state = env["sela.doc"]._fields["state"]
        # ("done",) places the new value before an existing one, keeping its label
        assert state.selection == [
            ("draft", "Draft"),
            ("sent", "Sent"),
            ("done", "Done"),
            ("cancel", "Cancelled"),
        ]
        assert state.ondelete == {"sent": "set default", "cancel": "cascade"}
        assert dict(state._get_selection_modules(env["sela.doc"])) == {
            "draft": {_BASE},
            "done": {_BASE},
            "sent": {_EXT},
            "cancel": {_EXT},
        }
        assert env["sela.doc"].fields_get(["state"])["state"]["selection"] == (
            state.selection
        )
        kind = env["sela.doc"]._fields["kind"]
        assert kind.selection == [("a", "A"), ("b", "B"), ("c", "C")]
        assert kind.ondelete == {"c": "set a"}
        doc = env["sela.doc"].create({"state": "sent", "kind": "c"})
        assert (doc.state, doc.kind) == ("sent", "c")
        with pytest.raises(
            ValueError, match=r"Wrong value for sela\.doc\.state: 'nope'"
        ):
            env["sela.doc"].create({"state": "nope"})


class RequiredWithoutPolicy(models.Model):
    _inherit = "sela.doc"
    _module = f"{_EXT}_requiredwithoutpolicy"

    kind = fields.Selection(selection_add=[("d", "D")])


class DefaultlessSetDefault(models.Model):
    _inherit = "sela.doc"
    _module = f"{_EXT}_defaultlesssetdefault"

    level = fields.Selection(
        selection_add=[("hi", "Hi")], ondelete={"hi": "set default"}
    )


class UnknownPolicy(models.Model):
    _inherit = "sela.doc"
    _module = f"{_EXT}_unknownpolicy"

    state = fields.Selection(
        selection_add=[("late", "Late")], ondelete={"late": "forget"}
    )


class SetUnknownValue(models.Model):
    _inherit = "sela.doc"
    _module = f"{_EXT}_setunknownvalue"

    state = fields.Selection(
        selection_add=[("late", "Late")], ondelete={"late": "set gone"}
    )


class AddOnDynamic(models.Model):
    _inherit = "sela.doc"
    _module = f"{_EXT}_addondynamic"

    mode = fields.Selection(selection_add=[("y", "Y")])


@pytest.mark.parametrize(
    ("extension", "error", "message"),
    [
        (RequiredWithoutPolicy, ValueError, "required selection fields must define"),
        (DefaultlessSetDefault, ValueError, "does not define a default"),
        (UnknownPolicy, ValueError, "not a valid ondelete"),
        (SetUnknownValue, ValueError, "'set null', 'set default', or 'set value'"),
        (AddOnDynamic, TypeError, "on non-list selection"),
    ],
)
def test_a_wrong_selection_add_is_refused_at_setup(extension, error, message):
    with pytest.raises(error, match=message), model_test_env(Doc, extension):
        pass

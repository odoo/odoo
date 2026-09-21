"""A field path that is not one never raises later: the compute simply stops
recomputing, or the onchange never fires. So the spellings that cannot be a
field path are refused where they are written."""

import pytest

from odoo import api


@pytest.mark.parametrize(
    ("decorator", "arg"),
    [
        (api.depends, "a, b"),
        (api.depends, "a,b"),
        (api.depends, "a b"),
        (api.depends, " a"),
        (api.depends, "a "),
        (api.depends, ""),
        (api.depends, "a..b"),
        (api.depends, ".a"),
        (api.depends, "a."),
        (api.depends, "a-b"),
        (api.depends, "a/b"),
        (api.constrains, "a, b"),
        (api.constrains, "a b"),
        (api.onchange, "a, b"),
        (api.onchange, "a.b"),
        (api.depends_context, "a.b"),
        (api.depends_context, "a, b"),
    ],
)
def test_a_spelling_that_cannot_be_a_field_path_is_refused(decorator, arg):
    with pytest.raises(ValueError, match="argument"):
        decorator(arg)


@pytest.mark.parametrize(
    ("decorator", "args"),
    [
        (api.depends, ()),
        (api.depends, ("a",)),
        (api.depends, ("a", "b")),
        (api.depends, ("a.b.c",)),
        (api.depends, ("x_studio_Partner",)),
        (api.constrains, ("line_ids.price",)),
        (api.constrains, ()),
        (api.onchange, ("partner_id",)),
        (api.depends_context, ("uid", "company")),
        (api.depends_context, ()),
    ],
)
def test_a_real_field_path_is_accepted(decorator, args):
    assert callable(decorator(*args))


def test_the_refusal_names_the_argument_and_the_reason():
    with pytest.raises(ValueError) as caught:
        api.depends("a, b")
    message = str(caught.value)
    assert "'a, b'" in message
    assert "comma" in message


def test_depends_on_id_is_still_refused_separately():
    with pytest.raises(NotImplementedError):
        api.depends("id")

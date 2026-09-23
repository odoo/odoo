from types import SimpleNamespace
from typing import cast

from odoo.orm.runtime.environment import Environment


def test_a_placeholder_may_be_named_source_or_self() -> None:
    env = cast("Environment", SimpleNamespace(lang=None))
    message = Environment._(
        env, "%(self)s was split off from %(source)s", self="B", source="A"
    )
    assert message == "B was split off from A"

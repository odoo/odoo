import inspect

from odoo.modules.registry import Registry
from odoo.tests.common import get_db_name, tagged

from .lint_case import LintCase, get_odoo_module_name

MODEL_METHODS_TO_IGNORE: set[tuple[str, str]] = set()

FAILURE_MESSAGE = """\
Onchange override in {model} narrows the trigger set of {method}.

{parent_module} declares @api.onchange{parent_triggers}
{child_module}  declares @api.onchange{child_triggers}

Dropped, and therefore dead for every database: {dropped}.

BaseModel._onchange_methods reads the trigger list off the MRO winner only, so the
override does not add to the parent's list -- it replaces it. Restate the full set, or
move the extension into a plain helper the onchange calls."""


def _triggers(method) -> frozenset[str] | None:
    fields = getattr(method, "_onchange", None)
    return None if fields is None else frozenset(fields)


@tagged("-at_install", "post_install")
class TestLintOnchangeTriggers(LintCase):
    def test_lint_onchange_override_does_not_narrow(self):
        registry = Registry(get_db_name())
        narrowed = []

        for model_name, model_cls in registry.items():
            for method_name, winner in inspect.getmembers(model_cls, inspect.isroutine):
                if (model_name, method_name) in MODEL_METHODS_TO_IGNORE:
                    continue
                declarations = [
                    (klass, klass.__dict__[method_name])
                    for klass in model_cls.mro()
                    if method_name in klass.__dict__
                    and _triggers(klass.__dict__[method_name]) is not None
                ]
                if len(declarations) < 2:
                    continue

                winner_triggers = _triggers(winner) or frozenset()
                winner_class = next(
                    (k for k in model_cls.mro() if method_name in k.__dict__), None
                )
                for parent_class, parent_method in declarations:
                    if parent_class is winner_class:
                        continue
                    dropped = _triggers(parent_method) - winner_triggers
                    if not dropped:
                        continue
                    narrowed.append(
                        FAILURE_MESSAGE.format(
                            model=model_name,
                            method=method_name,
                            parent_module=get_odoo_module_name(parent_class.__module__),
                            child_module=get_odoo_module_name(
                                winner_class.__module__ if winner_class else "?"
                            ),
                            parent_triggers=tuple(sorted(_triggers(parent_method))),
                            child_triggers=tuple(sorted(winner_triggers)),
                            dropped=", ".join(sorted(dropped)),
                        )
                    )
        self.assertFalse(narrowed, "\n\n".join(narrowed))

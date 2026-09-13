import inspect

from odoo.modules.registry import Registry
from odoo.tests.common import get_db_name, tagged

from .lint_case import LintCase

HOOK_ATTRIBUTES = ("compute", "inverse", "search", "selection", "group_expand")


@tagged("-at_install", "post_install")
class TestFieldDeclarations(LintCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = Registry(get_db_name())

    def test_every_hook_a_field_names_is_a_method_of_its_model(self):
        missing = []
        checked = 0
        for model_name, model_cls in self.registry.items():
            for field in model_cls._fields.values():
                for attribute in HOOK_ATTRIBUTES:
                    method = getattr(field, attribute, None)
                    if not isinstance(method, str):
                        continue
                    checked += 1
                    if not callable(getattr(model_cls, method, None)):
                        missing.append(
                            f"{model_name}.{field.name} {attribute}={method!r} "
                            f"({field._module})"
                        )
        self.assertGreater(checked, 100, "the scan reached almost no hooks")
        self.assert_ratchet(
            missing,
            "lint_field_hook_missing",
            "field hook(s) naming a method the model does not have",
            "Nothing checks the name at setup: resolve_mro() finds no method, the "
            "field gets no dependencies, and the first read raises AttributeError. "
            "Define the method, or on a mixin whose hosts supply it, declare the "
            "contract with a method that raises NotImplementedError.",
        )

    def test_every_onchange_and_constrains_names_a_field(self):
        unknown = []
        checked = 0
        for model_name, model_cls in self.registry.items():
            if model_cls._abstract:
                continue
            for attr_name, func in inspect.getmembers(model_cls, callable):
                for decorator in ("_onchange", "_constrains"):
                    names = getattr(func, decorator, None)
                    if not names or callable(names):
                        continue
                    checked += 1
                    unknown.extend(
                        f"{model_name}.{attr_name} @api.{decorator[1:]}({name!r})"
                        for name in names
                        if name not in model_cls._fields
                    )
        self.assertGreater(checked, 100, "the scan reached almost no decorators")
        self.assert_ratchet(
            unknown,
            "lint_field_trigger_unknown",
            "@api.onchange / @api.constrains parameter(s) naming no field",
            "The ORM logs a warning the first time the model's hooks are read and "
            "then never fires the method for that name: the constraint enforces "
            "nothing and the onchange never runs. Name the field.",
        )

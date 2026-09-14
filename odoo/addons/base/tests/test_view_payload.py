from odoo.models import BaseModel
from odoo.tests import TransactionCase, tagged
from odoo.tools import view_ir


@tagged("post_install", "-at_install")
class TestViewPayloadConsistency(TransactionCase):
    """A view payload carries its arch as a string and as the IR; the client
    reads the IR first. Every model that rewrites `get_view`/`get_views`
    must leave the two agreeing — or the client renders a tree the override
    never touched."""

    def _overriding_models(self):
        for name, model in self.env.registry.items():
            cls = type(self.env[name])
            if model._abstract and not model._auto:
                continue
            for klass in cls.__mro__:
                if klass is BaseModel:
                    break
                if "get_view" in klass.__dict__ or "get_views" in klass.__dict__:
                    yield name
                    break

    def test_every_override_keeps_arch_and_ir_agreeing(self):
        disagreeing = []
        checked = 0
        for name in sorted(set(self._overriding_models())):
            model = self.env[name]
            if model._abstract or (not model._auto and not model._table):
                continue
            try:
                result = model.get_views(
                    [
                        (False, view_type)
                        for view_type in ("form", "list", "search", "kanban")
                    ]
                )
            except Exception as error:
                self.fail(f"{name}: get_views raised {error!r}")
            for view_type, view in result["views"].items():
                checked += 1
                if view_ir.from_string(view["arch"]) != view_ir.Node.from_dict(
                    view["ir"]
                ):
                    disagreeing.append(f"{name}/{view_type}")
        self.assertGreater(checked, 0)
        self.assertEqual(disagreeing, [])

    def test_every_override_answers_without_the_arch(self):
        # the web client asks get_views for the IR alone (`options["arch"]`
        # False); an override that reads or rewrites `view["arch"]` after
        # the base drops it raises here, not in front of a user
        answered = 0
        for name in sorted(set(self._overriding_models())):
            model = self.env[name]
            if model._abstract or (not model._auto and not model._table):
                continue
            try:
                result = model.get_views(
                    [
                        (False, view_type)
                        for view_type in ("form", "list", "search", "kanban")
                    ],
                    {"arch": False, "toolbar": True, "load_filters": True},
                )
            except Exception as error:
                self.fail(f"{name}: get_views without the arch raised {error!r}")
            for view_type, view in result["views"].items():
                answered += 1
                self.assertNotIn("arch", view, f"{name}/{view_type}")
                self.assertIn("ir", view, f"{name}/{view_type}")
        self.assertGreater(answered, 0)

    def test_the_arch_option_leaves_the_others_alone(self):
        with_arch = self.env["res.partner"].get_views(
            [(False, "form")], {"toolbar": True}
        )
        without = self.env["res.partner"].get_views(
            [(False, "form")], {"toolbar": True, "arch": False}
        )
        self.assertEqual(
            {k: v for k, v in with_arch["views"]["form"].items() if k != "arch"},
            without["views"]["form"],
        )
        self.assertEqual(with_arch["models"], without["models"])

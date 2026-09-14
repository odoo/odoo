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

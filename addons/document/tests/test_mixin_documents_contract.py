"""`mixin.documents` is an extension API, so its hook signatures are a contract.

A model that inherits the mixin and redefines one of its hooks with a different
signature does not fail to load, does not fail a linter, and does not fail its
own tests -- it simply wins on the MRO and is then called by `document` with
arguments it was never written for.

Measured 2026-09-16 on `resource.asset`, which inherits `mixin.documents` and
defined `_prepare_document_vals(self, name, **extra)` next to the mixin's
`_prepare_document_vals(self, attachment)`. `ir.attachment._create_document`
called it with an `ir.attachment` and got back vals with **no
`attachment_id`** and `name` set to `ir.attachment(8474,)`, so every file
uploaded onto a centralized asset produced an empty document named after the
recordset. Nothing raised; the auto-creation debug channel even reported
`auto_document_created count=1`.

This checks the whole registry rather than that one model, because the next
occurrence will be in a module nobody thought to re-read.
"""

import inspect

from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestMixinDocumentsContract(TransactionCase):
    def _hooks(self):
        mixin = type(self.env["mixin.documents"])
        return {
            name: inspect.signature(getattr(mixin, name))
            for name in dir(mixin)
            if name.startswith("_get_document")
            or name in ("_prepare_document_vals", "_check_create_documents")
            if callable(getattr(mixin, name, None))
        }

    def test_the_hook_roster_is_not_empty(self):
        """Negative control: an empty roster would make the sweep vacuous."""
        hooks = self._hooks()
        self.assertIn("_prepare_document_vals", hooks)
        self.assertGreaterEqual(len(hooks), 5, sorted(hooks))

    def test_no_consumer_redefines_a_hook_with_another_signature(self):
        mixin_model = self.env["mixin.documents"]
        hooks = self._hooks()
        divergent = []
        for model_name in self.registry:
            if model_name == mixin_model._name:
                continue
            model_class = self.registry[model_name]
            if not issubclass(model_class, self.registry[mixin_model._name]):
                continue
            for hook, expected in hooks.items():
                found = getattr(model_class, hook, None)
                if found is None:
                    continue
                actual = inspect.signature(found)
                if list(actual.parameters) != list(expected.parameters):
                    divergent.append(
                        f"{model_name}.{hook}{actual} shadows "
                        f"mixin.documents.{hook}{expected} "
                        f"(defined in {inspect.getsourcefile(found)})"
                    )

        self.assertFalse(
            divergent,
            "a hook redefined with different parameters is called by "
            "`document` with the mixin's arguments and silently produces the "
            "wrong vals:\n  " + "\n  ".join(divergent),
        )

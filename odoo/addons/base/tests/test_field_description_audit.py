from unittest.mock import patch

from odoo.models import BaseModel
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.base.tests.common import TransactionCaseWithUserDemo


@tagged("post_install", "-at_install")
class TestFieldsGetAnswersForEveryModel(TransactionCase):
    def test_fields_get_never_raises_for_a_registered_model(self):
        failures = []
        for model_name in sorted(self.env.registry):
            model = self.env[model_name]
            try:
                model.fields_get()
            except Exception as error:
                failures.append(f"{model_name}: {type(error).__name__}: {error}")
        self.assertEqual(
            failures,
            [],
            "fields_get() is public API and must answer for every registered "
            "model, abstract ones included",
        )


@tagged("post_install", "-at_install")
class TestDescriptionProbesAreBestEffort(TransactionCase):
    def _get_field_not_backed_by_a_column(self, model):
        for field in model._fields.values():
            if not field.is_column:
                return field.name
        self.skipTest(f"{model._name} has no field outside its table")
        return None

    def test_a_model_that_cannot_build_a_query_still_describes_its_fields(self):
        model = self.env["res.partner"]
        fname = self._get_field_not_backed_by_a_column(model)

        def explode(*args, **kwargs):
            raise NotImplementedError("override _get_fields_select()")

        with patch.object(type(model), "_as_query", explode):
            description = model.fields_get(
                [fname], attributes=["sortable", "groupable"]
            )

        self.assertIn(fname, description)
        self.assertFalse(description[fname]["sortable"])
        self.assertFalse(description[fname]["groupable"])

    def test_a_query_that_raises_valueerror_is_answered_the_same_way(self):
        model = self.env["res.partner"]
        fname = self._get_field_not_backed_by_a_column(model)

        def explode(*args, **kwargs):
            raise ValueError("'' invalid for SQL.identifier()")

        with patch.object(type(model), "_as_query", explode):
            description = model.fields_get(
                [fname], attributes=["sortable", "groupable"]
            )

        self.assertFalse(description[fname]["sortable"])
        self.assertFalse(description[fname]["groupable"])


@tagged("post_install", "-at_install")
class TestFieldDescriptionMemo(TransactionCaseWithUserDemo):
    """`fields_get` composes each description from a half memoised per
    (model, attributes, field names, lang, su) and a half evaluated on every
    call. The composition must be indistinguishable from evaluating every
    attribute on every call."""

    @staticmethod
    def _uncached(model, attributes=None):
        described = {}
        for fname, field in model._fields.items():
            if not model._has_field_access(field, "read"):
                continue
            description = {}
            for attr, prop in field.description_attrs:
                if attributes is not None and attr not in attributes:
                    continue
                value = getattr(field, prop)
                if callable(value):
                    value = value(model.env)
                if value is not None:
                    description[attr] = value
            if "readonly" in description:
                description["readonly"] = description[
                    "readonly"
                ] or not model._has_field_access(field, "write")
            described[fname] = description
        return described

    def test_every_model_describes_as_if_uncached_for_the_demo_user(self):
        env = self.env(user=self.user_demo)
        attributes = env["base"]._get_view_field_attributes()
        differing = []
        compared = 0
        for model_name in sorted(env.registry):
            model = env[model_name]
            for wanted in (None, attributes):
                memoised = BaseModel.fields_get(model, attributes=wanted)
                expected = self._uncached(model, wanted)
                if not expected.keys() <= memoised.keys():
                    differing.append(f"{model_name}: fields missing")
                    continue
                for fname, description in expected.items():
                    for attr, value in description.items():
                        if memoised[fname].get(attr) != value:
                            differing.append(f"{model_name}.{fname}.{attr}")
                compared += len(expected)
        self.assertEqual(differing, [])
        self.assertGreater(compared, 2 * len(env.registry))

    def test_a_callable_selection_is_evaluated_on_every_call(self):
        Bank = self.env["res.partner.bank"]
        field = Bank._fields["acc_type"]
        self.assertIn("selection", field._dynamic_description_attrs(self.env))
        self.assertEqual(
            Bank.fields_get(["acc_type"], ["selection"])["acc_type"]["selection"],
            [("bank", "Normal")],
        )
        with patch.object(
            type(Bank),
            "_get_account_types_supported",
            lambda self: [("bank", "Normal"), ("iban", "IBAN")],
        ):
            self.assertEqual(
                Bank.fields_get(["acc_type"], ["selection"])["acc_type"]["selection"],
                [("bank", "Normal"), ("iban", "IBAN")],
            )

    def test_field_access_is_applied_per_user_over_one_memo(self):
        admin_fields = self.env["ir.actions.server"].fields_get(
            ["code", "name"], ["string", "readonly"]
        )
        demo_fields = (
            self.env["ir.actions.server"]
            .with_user(self.user_demo)
            .fields_get(["code", "name"], ["string", "readonly"])
        )
        self.assertIn("code", admin_fields)
        self.assertNotIn("code", demo_fields)
        self.assertIn("name", demo_fields)

    def test_the_caller_may_edit_a_description_without_touching_the_memo(self):
        Partner = self.env["res.partner"]
        first = Partner.fields_get(["type"], ["selection", "string"])["type"]
        first["selection"].append(("mutated", "Mutated"))
        first["string"] = "Mutated"
        second = Partner.fields_get(["type"], ["selection", "string"])["type"]
        self.assertNotIn(("mutated", "Mutated"), second["selection"])
        self.assertNotEqual(second["string"], "Mutated")

    def test_a_relabel_reaches_the_next_call(self):
        Partner = self.env(context={"lang": "en_US"})["res.partner"]
        self.assertEqual(
            Partner.fields_get(["comment"], ["string"])["comment"]["string"], "Notes"
        )
        self.env["ir.model.fields"]._get(Partner._name, "comment").write(
            {"field_description": "Remarks"}
        )
        self.assertEqual(
            Partner.fields_get(["comment"], ["string"])["comment"]["string"],
            "Remarks",
        )

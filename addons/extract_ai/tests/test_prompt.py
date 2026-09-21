from odoo.tests.common import BaseCase, tagged

from odoo.addons.extract.tools.schema import (
    FieldSpec,
    Schema,
    get_schema,
    known_schemas,
    sums_to,
)
from odoo.addons.extract_ai.models.prompt import prepare_prompt

_SCHEMA = Schema(
    name="test_bill",
    fields={
        "vendor": FieldSpec("str", help="Who issued it"),
        "issued_on": FieldSpec("date", required=True),
        "subtotal": FieldSpec("float"),
        "tax": FieldSpec("float"),
        "total": FieldSpec("float", required=True),
        "lines": FieldSpec(
            "list",
            items={
                "description": FieldSpec("str", required=True),
                "quantity": FieldSpec("float", help="Units, as printed"),
                "kind": FieldSpec("str", choices=("goods", "service")),
            },
        ),
    },
    rules=(sums_to("totals", ("subtotal", "tax"), "total"),),
    instructions="You read supplier bills for a Mexican agribusiness.",
)


@tagged("post_install", "-at_install")
class TestPrompt(BaseCase):
    def test_the_response_schema_asks_for_every_declared_field(self):
        shape = prepare_prompt(_SCHEMA).response_schema

        self.assertEqual(set(shape["properties"]), set(_SCHEMA.fields))

    def test_the_schema_instructions_open_the_system_prompt(self):
        system = prepare_prompt(_SCHEMA).system

        self.assertTrue(system.startswith("You read supplier bills"))

    def test_the_system_prompt_forbids_invention_and_fixes_formats(self):
        system = prepare_prompt(_SCHEMA).system

        self.assertIn("Never invent a value", system)
        self.assertIn("null", system)
        self.assertIn("YYYY-MM-DD", system)

    def test_required_fields_are_named_as_required(self):
        self.assertRegex(prepare_prompt(_SCHEMA).prompt, r"issued_on:.*required")

    def test_help_text_reaches_the_model(self):
        self.assertIn("Who issued it", prepare_prompt(_SCHEMA).prompt)

    def test_a_row_describes_its_own_fields(self):
        prompt = prepare_prompt(_SCHEMA).prompt

        self.assertIn("lines.quantity: Units, as printed", prompt)
        self.assertIn("lines.kind: one of: goods, service", prompt)

    def test_the_rules_the_answer_will_be_checked_against_are_stated(self):
        self.assertIn(
            "subtotal + tax should equal total", prepare_prompt(_SCHEMA).prompt
        )

    def test_a_row_declares_the_keys_it_wants(self):
        row = prepare_prompt(_SCHEMA).response_schema["properties"]["lines"]["items"]

        self.assertEqual(set(row["properties"]), {"description", "quantity", "kind"})
        self.assertEqual(row["properties"]["description"]["type"], "string")
        self.assertEqual(row["properties"]["kind"]["enum"], ["goods", "service", None])

    def test_a_row_says_which_of_its_keys_it_cannot_do_without(self):
        self.assertIn(
            "a row without description is not a row", prepare_prompt(_SCHEMA).prompt
        )

    def test_asking_for_two_fields_asks_about_two_fields(self):
        prepared = prepare_prompt(_SCHEMA, wanted=("total", "issued_on"))

        self.assertEqual(
            set(prepared.response_schema["properties"]), {"total", "issued_on"}
        )
        self.assertNotIn("vendor", prepared.prompt)

    def test_a_narrowed_prompt_keeps_only_the_rules_that_still_apply(self):
        prompt = prepare_prompt(_SCHEMA, wanted=("vendor",)).prompt

        self.assertNotIn("should equal total", prompt)

    def test_a_field_the_schema_does_not_have_is_ignored_not_echoed(self):
        prepared = prepare_prompt(_SCHEMA, wanted=("total", "made_up_field"))

        self.assertNotIn("made_up_field", prepared.prompt)
        self.assertNotIn("made_up_field", prepared.response_schema["properties"])

    def test_an_entirely_unknown_request_falls_back_to_the_whole_schema(self):
        shape = prepare_prompt(_SCHEMA, wanted=("nonsense",)).response_schema

        self.assertEqual(set(shape["properties"]), set(_SCHEMA.fields))

    def test_every_shipped_schema_produces_a_prompt(self):
        for name in known_schemas():
            with self.subTest(schema=name):
                prepared = prepare_prompt(get_schema(name))

                self.assertIn(name.replace("_", " "), prepared.prompt)
                self.assertEqual(
                    set(prepared.response_schema["properties"]),
                    set(get_schema(name).fields),
                )

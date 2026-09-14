from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools.json_payload import (
    parse_json_response,
    strip_json_fence,
)


@tagged("post_install", "-at_install")
class TestParseJsonResponse(TransactionCase):
    def test_plain_object(self):
        self.assertEqual(parse_json_response('{"a": 1}', self.env), {"a": 1})

    def test_plain_array(self):
        self.assertEqual(parse_json_response("[1, 2]", self.env), [1, 2])

    def test_surrounding_whitespace(self):
        self.assertEqual(parse_json_response('\n\n  {"a": 1}  \n', self.env), {"a": 1})

    def test_json_fence(self):
        text = 'Here you go:\n```json\n{"a": 1}\n```\nHope that helps.'
        self.assertEqual(parse_json_response(text, self.env), {"a": 1})

    def test_bare_fence(self):
        self.assertEqual(parse_json_response('```\n{"a": 1}\n```', self.env), {"a": 1})

    def test_fence_is_case_insensitive(self):
        self.assertEqual(
            parse_json_response('```JSON\n{"a": 1}\n```', self.env), {"a": 1}
        )

    def test_fenced_array(self):
        self.assertEqual(parse_json_response("```json\n[1, 2]\n```", self.env), [1, 2])

    def test_trailing_prose_after_object(self):
        text = '{"a": 1} — let me know if you need anything else.'
        self.assertEqual(parse_json_response(text, self.env), {"a": 1})

    def test_leading_prose_before_object(self):
        text = 'Sure! Here is the extraction: {"a": 1, "b": {"c": 2}}'
        self.assertEqual(parse_json_response(text, self.env), {"a": 1, "b": {"c": 2}})

    def test_scan_prefers_the_outermost_object(self):
        text = 'result: {"outer": {"inner": 1}} done'
        self.assertEqual(parse_json_response(text, self.env), {"outer": {"inner": 1}})

    def test_expect_dict_rejects_a_bare_array(self):
        with self.assertRaises(UserError):
            parse_json_response("[1, 2]", self.env, expect=(dict,))

    def test_expect_dict_still_finds_an_object_after_prose(self):
        self.assertEqual(
            parse_json_response('note {"a": 1}', self.env, expect=(dict,)),
            {"a": 1},
        )

    def test_empty_response_raises(self):
        with self.assertRaises(UserError):
            parse_json_response("", self.env)

    def test_whitespace_only_response_raises(self):
        with self.assertRaises(UserError):
            parse_json_response("   \n  ", self.env)

    def test_none_response_raises(self):
        with self.assertRaises(UserError):
            parse_json_response(None, self.env)

    def test_unparsable_raises_with_a_preview(self):
        with self.assertRaises(UserError) as ctx:
            parse_json_response("I'm sorry, I can't help with that.", self.env)
        self.assertIn("I'm sorry", str(ctx.exception))

    def test_preview_is_truncated(self):
        with self.assertRaises(UserError) as ctx:
            parse_json_response("x" * 500, self.env)
        self.assertIn("...", str(ctx.exception))

    def test_env_is_required(self):
        self.assertEqual(parse_json_response('{"a": 1}', self.env), {"a": 1})
        with self.assertRaises(TypeError):
            parse_json_response('{"a": 1}')


@tagged("post_install", "-at_install")
class TestStripJsonFence(TransactionCase):
    def test_fenced_block_with_language(self):
        self.assertEqual(strip_json_fence('```json\n{"a": 1}\n```'), '{"a": 1}')

    def test_fenced_block_without_language(self):
        self.assertEqual(strip_json_fence('```\n{"a": 1}\n```'), '{"a": 1}')

    def test_unfenced_text_is_returned_stripped(self):
        self.assertEqual(strip_json_fence('\n  {"a": 1}  \n'), '{"a": 1}')

    def test_prose_before_the_fence(self):
        text = 'Here you go:\n```json\n{"a": 1}\n```\nHope that helps.'
        self.assertEqual(strip_json_fence(text), '{"a": 1}')

    def test_empty_and_none(self):
        self.assertEqual(strip_json_fence(""), "")
        self.assertEqual(strip_json_fence(None), "")

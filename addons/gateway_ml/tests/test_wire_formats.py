from odoo.tests.common import TransactionCase

from odoo.addons.gateway_ml.tools import (
    ClaudeClient,
    read_anthropic_content,
    read_openai_content,
)
from odoo.addons.integration.tools import CommError


class TestSharedResponseReaders(TransactionCase):
    def test_anthropic_reader_joins_every_text_block(self):
        text, problem = read_anthropic_content(
            {
                "content": [
                    {"type": "text", "text": "one "},
                    {"type": "text", "text": "two"},
                ],
                "stop_reason": "end_turn",
            }
        )
        self.assertIsNone(problem)
        self.assertEqual(text, "one two")

    def test_anthropic_reader_survives_a_leading_thinking_block(self):
        text, problem = read_anthropic_content(
            {
                "content": [
                    {"type": "thinking", "thinking": "let me consider"},
                    {"type": "text", "text": "the answer"},
                ],
                "stop_reason": "end_turn",
            }
        )
        self.assertIsNone(problem)
        self.assertEqual(text, "the answer")

    def test_anthropic_reader_refuses_a_truncated_answer(self):
        text, problem = read_anthropic_content(
            {
                "content": [{"type": "text", "text": '{"partial"'}],
                "stop_reason": "max_tokens",
            }
        )
        self.assertEqual(text, "")
        self.assertIn("truncated", problem)

    def test_openai_reader_refuses_a_truncated_answer(self):
        text, problem = read_openai_content(
            {
                "choices": [
                    {"message": {"content": '{"partial"'}, "finish_reason": "length"}
                ]
            }
        )
        self.assertEqual(text, "")
        self.assertIn("truncated", problem)

    def test_openai_reader_accepts_a_finished_answer(self):
        text, problem = read_openai_content(
            {"choices": [{"message": {"content": "done"}, "finish_reason": "stop"}]}
        )
        self.assertIsNone(problem)
        self.assertEqual(text, "done")

    def test_readers_refuse_a_non_dict_payload(self):
        for reader in (read_openai_content, read_anthropic_content):
            with self.subTest(reader=reader.__name__):
                text, problem = reader("not a dict")
                self.assertEqual(text, "")
                self.assertIn("JSON object", problem)

    def test_the_class_stack_reads_a_thinking_first_response(self):
        client = ClaudeClient.__new__(ClaudeClient)
        self.assertEqual(
            client._extract_text_from_response(
                {
                    "content": [
                        {"type": "thinking", "thinking": "…"},
                        {"type": "text", "text": "the answer"},
                    ],
                    "stop_reason": "end_turn",
                }
            ),
            "the answer",
        )

    def test_the_class_stack_refuses_a_truncated_response(self):
        client = ClaudeClient.__new__(ClaudeClient)
        with self.assertRaises(CommError) as caught:
            client._extract_text_from_response(
                {
                    "content": [{"type": "text", "text": "half"}],
                    "stop_reason": "max_tokens",
                }
            )
        self.assertIn("truncated", str(caught.exception))

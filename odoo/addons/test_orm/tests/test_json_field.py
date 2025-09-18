from odoo.tests.common import TransactionCase


class JsonFieldTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.discussion_1 = cls.env["test_orm.discussion"].create(
            {
                "name": "Test Discussion JSON field",
            }
        )

    def test_json_field_read_write(self):
        random_str = "tVpajMuSvaR94DwSRVtRSLGNkKViNbWHt2hq13"
        random_str_2 = "Crypto-money base"

        self.assertEqual(self.discussion_1.history, {"delete_messages": []})

        # Check that it is not the value of the cache return by convert_to_record
        history_field = type(self.discussion_1).history
        self.assertIsNot(
            self.discussion_1.history,
            self.env._core.get_value(history_field, self.discussion_1.id),
        )

        self.assertEqual(self.discussion_1.history, {"delete_messages": []})

        self.discussion_1.history = {"delete_messages": [random_str]}
        self.discussion_1.flush_recordset()
        self.assertEqual(self.discussion_1.history, {"delete_messages": [random_str]})

        self.discussion_1.history = {"delete_messages": [random_str, random_str_2]}
        self.discussion_1.flush_recordset()

        self.assertEqual(
            self.discussion_1.history,
            {"delete_messages": [random_str, random_str_2]},
        )

        self.discussion_1.history = (random_str, random_str_2)
        self.discussion_1.flush_recordset()

        self.assertEqual(self.discussion_1.history, [random_str, random_str_2])

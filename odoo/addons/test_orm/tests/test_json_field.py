from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class JsonFieldTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.discussion_1 = cls.env['test_fields.misc'].create({})

    def test_json_field_read_write(self):
        random_str = "tVpajMuSvaR94DwSRVtRSLGNkKViNbWHt2hq13"
        random_str_2 = "Crypto-money base"

        self.assertEqual(self.discussion_1.json_default, {'values': []})

        # Check that it is not the value of the cache return by convert_to_record
        self.assertIsNot(self.discussion_1.json_default, self.discussion_1._cache['json_default'])

        self.assertEqual(self.discussion_1.json_default, {'values': []})

        self.discussion_1.json_default = {'values': [random_str]}
        self.discussion_1.flush_recordset()
        self.assertEqual(self.discussion_1.json_default, {'values': [random_str]})

        self.discussion_1.json_default = {'values': [random_str, random_str_2]}
        self.discussion_1.flush_recordset()

        self.assertEqual(self.discussion_1.json_default, {'values': [random_str, random_str_2]})

        self.discussion_1.json_default = (random_str, random_str_2)
        self.discussion_1.flush_recordset()

        self.assertEqual(self.discussion_1.json_default, [random_str, random_str_2])

from odoo.tests.common import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class JsonFieldTest(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.json_field = cls.env['test_orm.json_field'].create({})

    def test_json_field_read_write(self):
        random_str = "tVpajMuSvaR94DwSRVtRSLGNkKViNbWHt2hq13"
        random_str_2 = "Crypto-money base"

        self.assertEqual(self.json_field.value, {'data': []})

        # Check that it is not the value of the cache return by convert_to_record
        self.assertIsNot(self.json_field.value, self.json_field._cache['value'])

        self.assertEqual(self.json_field.value, {'data': []})

        self.json_field.value = {'data': [random_str]}
        self.json_field.flush_recordset()
        self.assertEqual(self.json_field.value, {'data': [random_str]})

        self.json_field.value = {'data': [random_str, random_str_2]}
        self.json_field.flush_recordset()

        self.assertEqual(self.json_field.value, {'data': [random_str, random_str_2]})

        self.json_field.value = (random_str, random_str_2)
        self.json_field.flush_recordset()

        self.assertEqual(self.json_field.value, [random_str, random_str_2])

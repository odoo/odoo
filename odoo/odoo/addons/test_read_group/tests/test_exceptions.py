from odoo.tests import common


class TestExceptions(common.TransactionCase):
    """ Test what happens when grouping unknown fields or aggregates. """

    def setUp(self):
        super().setUp()
        self.Model = self.env['test_read_group.aggregate']

    def test_unkonwn_field(self):
        with self.assertRaisesRegex(ValueError, "Invalid field 'unknown_field' on model"):
            self.Model.read_group([], ['unknown_field'], ['partner_id'])

        with self.assertRaisesRegex(ValueError, "Invalid field 'unknown_field' on model"):
            self.Model.read_group([], ['partner_id'], ['unknown_field'])

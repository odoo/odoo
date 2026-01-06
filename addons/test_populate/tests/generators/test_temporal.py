import re

from odoo.tests import TransactionCase

from odoo.addons.populate.generators import Date, Datetime


class TestDateGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.created_date_field = test_product_model._fields['created_date']

    def test_date_generator(self):
        generator = Date(
            field=self.created_date_field,
            env=self.env,
            start='today',
            end='today +1m',
        )

        values = [generator.next({}) for _ in range(10)]

        date_pattern = r'\d{4}-\d{2}-\d{2}'
        self.assertTrue(all(re.match(date_pattern, val) for val in values))


class TestDatetimeGenerator(TransactionCase):

    def setUp(self):
        super().setUp()
        test_product_model = self.env['test_populate.product']
        self.updated_at_field = test_product_model._fields['updated_at']

    def test_datetime_generator(self):
        generator = Datetime(
            field=self.updated_at_field,
            env=self.env,
            start='now',
            end='now +1d',
        )

        values = [generator.next({}) for _ in range(10)]

        datetime_pattern = r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        self.assertTrue(all(re.match(datetime_pattern, val) for val in values))

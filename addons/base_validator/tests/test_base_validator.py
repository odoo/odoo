# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import common


class BaseValidator(common.TransactionCase):

    def test_01(self):
        """ Validator output is correct (include value, name, help message
        """
        validator = self.env.ref('base_validator.base_validator_demo')
        validator.input_test_string = '5123'
        self.assertEqual(
            validator.output_test_string,
            "'5123' is not a valid value for 'Test Validator'.\n"
            "The number should have 16 char length")

        validator.input_test_string = '1234567890123456'
        self.assertEqual(validator.output_test_string, '1234567890123456')

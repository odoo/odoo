# Part of Odoo. See LICENSE file for full copyright and licensing details.
import unittest
from odoo.tests import tagged
from odoo.exceptions import UserError
# noinspection PyUnresolvedReferences
from ..models.account_move \
    import compute_payment_reference_finnish, compute_payment_reference_finnish_rf


@tagged('standard', 'at_install')
class PaymentReferenceTest(unittest.TestCase):

    """
    All references validated with the reference calculator by Nordea Bank
    http://www.nordea.fi/en/corporate-customers/payments/invoicing-and-payments/reference-number-calculator.html
    """

    def test_payment_reference_fi(self):

        compute = compute_payment_reference_finnish

        # Common
        self.assertEqual('1232', compute('INV123'))
        self.assertEqual('1326', compute('132'))
        self.assertEqual('1290', compute('ABC1B2B9C'))

        # Insufficient
        self.assertEqual('1119', compute('-1'))
        self.assertEqual('1106', compute('0'))
        self.assertEqual('1261', compute('26'))

        # Excess length
        self.assertEquals('12345678901234567894',
                          compute('123456789012345678901234567890'))

        # Invalid
        # noinspection PyBroadException
        try:
            compute('QWERTY')
            self.fail('Provided a FI payment reference for QWERTY')
        except UserError:
            # All good
            pass

    def test_payment_reference_rf(self):

        compute = compute_payment_reference_finnish_rf

        # Common
        self.assertEqual('RF111232', compute('INV123'))
        self.assertEqual('RF921326', compute('132'))
        self.assertEqual('RF941290', compute('ABC1B2B9C'))

        # Insufficient
        self.assertEqual('RF551119', compute('-1'))
        self.assertEqual('RF181106', compute('0'))
        self.assertEqual('RF041261', compute('26'))

        # Excess length
        self.assertEquals('RF0912345678901234567894',
                          compute('123456789012345678901234567890'))

        # Invalid
        # noinspection PyBroadException
        try:
            compute('QWERTY')
            self.fail('Provided a RF payment reference for QWERTY')
        except UserError:
            # All good
            pass

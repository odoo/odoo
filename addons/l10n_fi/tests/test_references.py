# -*- coding: utf-8 -*-
import unittest
from openerp.exceptions import UserError
# noinspection PyUnresolvedReferences
from openerp.addons.l10n_fi.models.account_invoice \
    import compute_payment_reference_fi, compute_payment_reference_rf


class PaymentReferenceTest(unittest.TestCase):

    """
    All references validated with the reference calculator by Nordea Bank
    http://www.nordea.fi/en/corporate-customers/payments/invoicing-and-payments/reference-number-calculator.html
    """

    def test_payment_reference_fi(self):

        compute = compute_payment_reference_fi

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

        compute = compute_payment_reference_rf

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

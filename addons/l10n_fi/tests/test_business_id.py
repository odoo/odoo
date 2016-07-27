# -*- coding: utf-8 -*-
import unittest
from openerp.exceptions import ValidationError
# noinspection PyUnresolvedReferences
from openerp.addons.l10n_fi.models.res_partner import check_business_id


class BusinessIDTest(unittest.TestCase):

    def test_business_ids(self):

        # Common
        self.assertTrue(check_business_id('2413456-4'))
        self.assertTrue(check_business_id('2349368-8'))
        self.assertTrue(check_business_id('115733-3'))
        self.assertTrue(check_business_id('0115733-3'))

        # Invalid
        try:
            check_business_id('2349368-4')
            self.fail('Validated 2349368-4 as a valid Business ID while '
                      'it has an invalid check digit')
        except ValidationError:
            # All good
            pass

        try:
            check_business_id('QWERTY')
            self.fail('Validated QWERTY as a valid Business ID when it\'s not')
        except ValidationError:
            # All good
            pass

        try:
            check_business_id(False)
            self.fail('Validated a boolean value as a valid Business ID')
        except ValidationError:
            # All good
            pass

        try:
            check_business_id(123)
            self.fail('Validated an integer value as a valid Business ID')
        except ValidationError:
            # All good
            pass


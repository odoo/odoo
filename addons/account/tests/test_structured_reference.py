from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.account.tools import (
    is_valid_structured_reference_be,
    is_valid_structured_reference_fi,
    is_valid_structured_reference_no_se,
    is_valid_structured_reference_iso,
    is_valid_structured_reference,
)


@tagged('standard', 'at_install')
class StructuredReferenceTest(TransactionCase):

    def test_structured_reference_iso(self):
        # Accepts references in structured format
        self.assertTrue(is_valid_structured_reference_iso(' RF18 5390 0754 7034 '))
        # Accept references in unstructured format
        self.assertTrue(is_valid_structured_reference_iso(' RF18539007547034'))
        # Validates with zero's added in front
        self.assertTrue(is_valid_structured_reference_iso('RF18000000000539007547034'))

        # Does not validate invalid structured format
        self.assertFalse(is_valid_structured_reference_iso('18539007547034RF'))
        # Does not validate invalid checksum
        self.assertFalse(is_valid_structured_reference_iso('RF17539007547034'))
        # Validates the entire string
        self.assertFalse(is_valid_structured_reference_be('RF18539007547034-OTHER-RANDOM-STUFF'))

    def test_structured_reference_be(self):
        # Accepts references in both structured formats
        self.assertTrue(is_valid_structured_reference_be(' +++020/3430/57642+++'))
        self.assertTrue(is_valid_structured_reference_be('***020/3430/57642*** '))
        # Accept references in unstructured format
        self.assertTrue(is_valid_structured_reference_be(' 020343057642'))
        # Validates edge case where result of % 97 = 0
        self.assertTrue(is_valid_structured_reference_be('020343053497'))

        # Does not validate invalid structured format
        self.assertFalse(is_valid_structured_reference_be('***02/03430/57642***'))
        # Does not validate invalid checksum
        self.assertFalse(is_valid_structured_reference_be('020343057641'))
        # Validates the entire string
        self.assertFalse(is_valid_structured_reference_be('020343053497-OTHER-RANDOM-STUFF'))

    def test_structured_reference_fi(self):
        # Accepts references in structured format
        self.assertTrue(is_valid_structured_reference_fi('2023 0000 98'))
        # Accept references in unstructured format
        self.assertTrue(is_valid_structured_reference_fi('2023000098'))
        # Validates with zero's added in front
        self.assertTrue(is_valid_structured_reference_fi('00000000002023000098'))

        # Does not validate invalid structured format
        self.assertFalse(is_valid_structured_reference_fi('2023/0000/98'))
        # Does not validate invalid length
        self.assertFalse(is_valid_structured_reference_fi('000000000002023000098'))
        # Does not validate invalid checksum
        self.assertFalse(is_valid_structured_reference_fi('2023000095'))
        # Validates the entire string
        self.assertFalse(is_valid_structured_reference_fi('2023000098-OTHER-RANDOM-STUFF'))

    def test_structured_reference_no_se(self):
        # Accepts references in structured format
        self.assertTrue(is_valid_structured_reference_no_se('1234 5678 97'))
        # Accept references in unstructured format
        self.assertTrue(is_valid_structured_reference_no_se('1234567897'))
        # Validates with zero's added in front
        self.assertTrue(is_valid_structured_reference_no_se('000001234567897'))

        # Does not validate invalid structured format
        self.assertFalse(is_valid_structured_reference_no_se('1234/5678/97'))
        # Does not validate invalid checksum
        self.assertFalse(is_valid_structured_reference_no_se('1234567898'))
        # Validates the entire string
        self.assertFalse(is_valid_structured_reference_no_se('1234567897-OTHER-RANDOM-STUFF'))

    def test_structured_reference(self):
        # Accepts references in structured format
        self.assertTrue(is_valid_structured_reference(' RF18 5390 0754 7034 '))  # ISO
        self.assertTrue(is_valid_structured_reference(' +++020/3430/57642+++'))  # BE
        self.assertTrue(is_valid_structured_reference('***020/3430/57642*** '))  # BE
        self.assertTrue(is_valid_structured_reference('2023 0000 98'))  # FI
        self.assertTrue(is_valid_structured_reference('1234 5678 97'))  # NO-SE
        # Accept references in unstructured format
        self.assertTrue(is_valid_structured_reference(' RF18539007547034'))  # ISO
        self.assertTrue(is_valid_structured_reference(' 020343057642'))  # BE
        self.assertTrue(is_valid_structured_reference('2023000098'))  # FI
        self.assertTrue(is_valid_structured_reference('1234567897'))  # NO-SE
        # Validates with zero's added in front
        self.assertTrue(is_valid_structured_reference('RF18000000000539007547034'))  # ISO
        self.assertTrue(is_valid_structured_reference('00000000002023000098'))  # FI
        self.assertTrue(is_valid_structured_reference('000001234567897'))  # NO-SE

        # Does not validate invalid structured format
        self.assertFalse(is_valid_structured_reference('18539007547034RF'))  # ISO
        self.assertFalse(is_valid_structured_reference('***02/03430/57642***'))  # BE
        self.assertFalse(is_valid_structured_reference('2023/0000/98'))  # FI
        self.assertFalse(is_valid_structured_reference('1234/5678/97'))  # NO-SE
        # Does not validate invalid checksum
        self.assertFalse(is_valid_structured_reference('RF17539007547034'))  # ISO
        self.assertFalse(is_valid_structured_reference('020343057641'))  # BE
        self.assertFalse(is_valid_structured_reference('2023000095'))  # FI
        self.assertFalse(is_valid_structured_reference('1234567898'))  # NO-SE

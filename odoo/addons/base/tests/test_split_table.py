from odoo.tests.common import TransactionCase
from odoo.tools import file_open
from odoo.addons.base.models.ir_actions_report import _split_table
from lxml import etree

def cleanup_string(s):
    return ''.join(s.split())

class TestSplitTable(TransactionCase):
    def test_split_table(self):
        # NOTE: All the tests's xml are in split_table/ relative to this file
        CASES = (
            ("Table's len is equal to max_rows and should not be split", "simple", "simple", 3),
            ("Table's len is greater to max_rows and should not be split", "simple", "simple", 4),
            ("max_rows is 1 and every table should be split", "simple", "simple.split1", 1),
            ("max_row is 2 and the table should be split", "simple", "simple.split2", 2),
            ("Nested tables should be split", "nested", "nested.split2", 2),
            ("Nested tables at the start should be split", "first_nested", "first_nested.split2", 2),
            ("Attributes should be copied", "copy_attributes", "copy_attributes.split1", 1),
        )

        for description, actual, expected, max_rows in CASES:
            with self.subTest(description), \
                file_open(f"base/tests/split_table/{actual}.xml") as actual, \
                file_open(f"base/tests/split_table/{expected}.xml") as expected:

                tree = etree.fromstring(actual.read())
                _split_table(tree, max_rows)
                processed = etree.tostring(tree, encoding='unicode')
                self.assertEqual(cleanup_string(processed), cleanup_string(expected.read()))

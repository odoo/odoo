from odoo.tests import BaseCase
from odoo.tests.diffcase import DiffCase
from odoo.tools import file_path


class TestDiffCase(BaseCase):
    def get_diff_linenos(self, filepath: str, *args, expected_lines: int | None = None) -> set[int]:
        modified_lines: set[str] = set(l.strip() for l in args)
        diff_linenos: set[int] = set()
        with open(filepath, 'r') as fp:
            for lineno, line in enumerate(fp, start=1):
                if line.strip() in modified_lines:
                    diff_linenos.add(lineno)
        if expected_lines is not None:
            self.assertEqual(len(diff_linenos), expected_lines)
        return diff_linenos
    
    def test_yield_xml_diff_elements(self):
        abs_path = file_path('test_lint/tests/data/test_diff_case.xml')
        diff_linenos = self.get_diff_linenos(
            abs_path,
            'model="res.users.settings"',
            expected_lines=1,
        )

        elements = list([e for e in DiffCase.get_xml_elements(abs_path, diff_linenos) if e.start_tag_in_diff])
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'record')
        self.assertEqual(elements[0].get('model', None), 'res.users.settings')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '<field name="login">admin</field><field name="password">admin</field>',
            expected_lines=1,
        )
        elements = list([e for e in DiffCase.get_xml_elements(abs_path, diff_linenos) if e.start_tag_in_diff])
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0].tag, 'field')
        self.assertEqual(elements[0].get('name', None), 'login')
        self.assertEqual(elements[1].tag, 'field')
        self.assertEqual(elements[1].get('name', None), 'password')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '/> <!-- end of user admin -->',
            expected_lines=1,
        )
        elements = list([e for e in DiffCase.get_xml_elements(abs_path, diff_linenos) if e.start_tag_in_diff])
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'field')
        self.assertEqual(elements[0].get('ref', None), 'base.partner_admin')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:tns="http://www.sbr.gov.au/ato/payevnt"',
            expected_lines=1,
        )
        elements = list([e for e in DiffCase.get_xml_elements(abs_path, diff_linenos) if e.start_tag_in_diff])
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, '{http://www.sbr.gov.au/ato/payevnt}PAYEVNT')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '<tns:Rp>',
            expected_lines=1,
        )
        elements = list([e for e in DiffCase.get_xml_elements(abs_path, diff_linenos) if e.start_tag_in_diff])
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, '{http://www.sbr.gov.au/ato/payevnt}Rp')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '</record> <!-- end of user admin -->',
            '<!-- user admin settings first line',
            'second line -->',
            expected_lines=3,
        )
        elements = list([e for e in DiffCase.get_xml_elements(abs_path, diff_linenos) if e.start_tag_in_diff])
        self.assertFalse(elements)

        # The <?xml version="1.0" encoding="utf-8"?> won't be parsed by iterparse
        # We don't handle it for simplicity. As a result, it will be treated as part of the first element by the implementation
        diff_linenos = self.get_diff_linenos(
            abs_path,
            '<?xml version="1.0" encoding="utf-8"?>',
            expected_lines=1,
        )
        elements = list([e for e in DiffCase.get_xml_elements(abs_path, diff_linenos) if e.start_tag_in_diff])
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'odoo')

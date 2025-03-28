from odoo.tests import BaseCase
from odoo.tests.diffcase import DiffCase
from odoo.tools import file_path


class TestDiffCase(BaseCase):
    def get_diff_linenos(self, filepath: str, *args, expected_lines: int | None = None) -> set[int]:
        """ get the line numbers of the lines that are in the args and check if the number of lines is expected_lines """
        modified_lines: set[str] = {l.strip() for l in args}
        diff_linenos: set[int] = set()
        with open(filepath, encoding='utf-8') as f:
            for lineno, line in enumerate(f, start=1):
                if line.strip() in modified_lines:
                    diff_linenos.add(lineno)
        if expected_lines is not None:
            self.assertEqual(len(diff_linenos), expected_lines)
        return diff_linenos

    def test_get_xml_elements(self):
        abs_path = file_path('test_lint/tests/data/test_diff_case.xml')
        diff_linenos = self.get_diff_linenos(
            abs_path,
            'model="res.users.settings"',   # line in a multi-line start tag
            expected_lines=1,
        )

        element_tree, elements_info = DiffCase.parse_xml_file(abs_path, diff_linenos)
        elements = [e for e in element_tree.iter() if isinstance(e.tag, str) and elements_info[e].start_tag_in_diff]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'record')
        self.assertEqual(elements[0].get('model', None), 'res.users.settings')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '<field name="login">admin</field><field name="password">admin</field>',  # 2 elements in a single line
            expected_lines=1,
        )
        element_tree, elements_info = DiffCase.parse_xml_file(abs_path, diff_linenos)
        elements = [e for e in element_tree.iter() if isinstance(e.tag, str) and elements_info[e].start_tag_in_diff]
        self.assertEqual(len(elements), 2)
        self.assertEqual(elements[0].tag, 'field')
        self.assertEqual(elements[0].get('name', None), 'login')
        self.assertEqual(elements[1].tag, 'field')
        self.assertEqual(elements[1].get('name', None), 'password')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '/> <!-- end of user admin -->',  # start tag closes in a different line
            expected_lines=1,
        )
        element_tree, elements_info = DiffCase.parse_xml_file(abs_path, diff_linenos)
        elements = [e for e in element_tree.iter() if isinstance(e.tag, str) and elements_info[e].start_tag_in_diff]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'field')
        self.assertEqual(elements[0].get('ref', None), 'base.partner_admin')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:tns="http://www.sbr.gov.au/ato/payevnt"',  # line in a namespace
            expected_lines=1,
        )
        element_tree, elements_info = DiffCase.parse_xml_file(abs_path, diff_linenos)
        elements = [e for e in element_tree.iter() if isinstance(e.tag, str) and elements_info[e].start_tag_in_diff]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, '{http://www.sbr.gov.au/ato/payevnt}PAYEVNT')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '<tns:Rp>',  # start tag of a namespace
            expected_lines=1,
        )
        element_tree, elements_info = DiffCase.parse_xml_file(abs_path, diff_linenos)
        elements = [e for e in element_tree.iter() if isinstance(e.tag, str) and elements_info[e].start_tag_in_diff]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, '{http://www.sbr.gov.au/ato/payevnt}Rp')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '</record> <!-- end of user admin -->',  # comment after end tag
            '<!-- user admin settings first line',  # first line of a multi-line comment
            'second line -->',  # last line of a multi-line comment
            expected_lines=3,
        )
        element_tree, elements_info = DiffCase.parse_xml_file(abs_path, diff_linenos)
        elements = [e for e in element_tree.iter() if isinstance(e.tag, str) and elements_info[e].start_tag_in_diff]
        self.assertFalse(elements)

        # The <?xml version="1.0" encoding="utf-8"?> won't be parsed by iterparse
        # We don't handle it for simplicity. As a result, it will be treated as part of the first element by the implementation
        diff_linenos = self.get_diff_linenos(
            abs_path,
            '<?xml version="1.0" encoding="utf-8"?>',  # xml declaration
            expected_lines=1,
        )
        element_tree, elements_info = DiffCase.parse_xml_file(abs_path, diff_linenos)
        elements = [e for e in element_tree.iter() if isinstance(e.tag, str) and elements_info[e].start_tag_in_diff]
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'odoo')

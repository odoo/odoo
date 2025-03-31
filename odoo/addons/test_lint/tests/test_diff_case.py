from .diff_case import DiffCase
from odoo.tools import file_path


class TestDiffCase(DiffCase):
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
        abs_path = file_path('test_lint/tests/data/res_users_data.xml')
        diff_linenos = self.get_diff_linenos(
            abs_path,
            'model="res.users.settings"',
            expected_lines=1,
        )

        elements = list(self.yield_xml_diff_elements(abs_path, diff_linenos))
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'record')
        self.assertEqual(elements[0].get('model', None), 'res.users.settings')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '<field name="login">admin</field><field name="password">admin</field>',
            expected_lines=1,
        )
        elements = list(self.yield_xml_diff_elements(abs_path, diff_linenos))
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
        elements = list(self.yield_xml_diff_elements(abs_path, diff_linenos))
        self.assertEqual(len(elements), 1)
        self.assertEqual(elements[0].tag, 'field')
        self.assertEqual(elements[0].get('ref', None), 'base.partner_admin')

        diff_linenos = self.get_diff_linenos(
            abs_path,
            '</record> <!-- end of user admin -->',
            '<!-- user admin settings first line',
            'second line -->',
            expected_lines=3,
        )
        elements = list(self.yield_xml_diff_elements(abs_path, diff_linenos))
        self.assertFalse(elements)

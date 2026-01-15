from odoo.tests.common import TransactionCase

from odoo.addons.portal.controllers.portal import pager


class TestPager(TransactionCase):

    def test_pager_functionality(self):
        """Test the custom pager functionality."""
        test_cases = [
            # Case 1: Total items fit in one page
            {'total': 20, 'page': 1, 'expected_pages': [1]},
            # Case 2: Exactly two pages, first page active
            {'total': 50, 'page': 1, 'expected_pages': [1, 2]},
            # Case 3: Exactly five pages, middle page active
            {'total': 150, 'page': 3, 'expected_pages': [1, 2, 3, 4, 5]},
            # Case 4: Large number of pages, ellipses in the middle
            {'total': 300, 'page': 5, 'expected_pages': [1, '…', 4, 5, 6, '…', 10]},
            # Case 5: Large number of pages, first page active
            {'total': 300, 'page': 1, 'expected_pages': [1, 2, 3, 4, '…', 10]},
            # Case 6: Large number of pages, last page active
            {'total': 300, 'page': 10, 'expected_pages': [1, '…', 7, 8, 9, 10]},
        ]
        for case in test_cases:
            result = pager(
                url=case.get('url', '/test'),
                total=case['total'],
                page=case['page'],
                step=30,
                scope=5,
                url_args=None,
            )

            # Calculate expected page count
            expected_page_count = (case['total'] + 30 - 1) // 30
            pages = [p['num'] for p in result['pages']]

            # Assertions
            with self.subTest(case=case):
                self.assertEqual(
                    pages,
                    case['expected_pages'],
                    f"Expected pages mismatch for case: {case}"
                )
                self.assertEqual(
                    result['page']['num'],
                    case['page'],
                    f"Current page mismatch for case: {case}"
                )
                self.assertEqual(
                    result['page_count'],
                    expected_page_count,
                    f"Page count mismatch for case: {case}"
                )

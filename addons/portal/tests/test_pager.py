import logging
from urllib.parse import parse_qsl, urlsplit

from odoo.tests.common import TransactionCase

from odoo.addons.portal.controllers.portal import pager

_logger = logging.getLogger(__name__)


class TestPager(TransactionCase):
    def test_pager_preserves_url_components_and_repeated_filters(self):
        arguments = {"tag": ["new one", "new+two"], "blank": "", "ignored": None}
        result = pager(
            "https://example.test/my/orders?keep=1&keep=2&tag=old#results",
            total=90,
            page=2,
            url_args=arguments,
        )
        for key, path in (
            ("page_first", "/my/orders"),
            ("page", "/my/orders/page/2"),
            ("page_last", "/my/orders/page/3"),
        ):
            with self.subTest(key=key):
                parsed = urlsplit(result[key]["url"])
                _logger.debug("Pager URL %s: %s", key, parsed)
                self.assertEqual(parsed.scheme, "https")
                self.assertEqual(parsed.netloc, "example.test")
                self.assertEqual(parsed.path, path)
                self.assertEqual(parsed.fragment, "results")
                self.assertEqual(
                    parse_qsl(parsed.query, keep_blank_values=True),
                    [
                        ("keep", "1"),
                        ("keep", "2"),
                        ("tag", "new one"),
                        ("tag", "new+two"),
                        ("blank", ""),
                    ],
                )
        self.assertEqual(arguments["tag"], ["new one", "new+two"])
        self.assertIn("ignored", arguments)

    def test_pager_preserves_existing_query_without_new_arguments(self):
        for arguments in (None, {}, {"ignored": None}):
            with self.subTest(arguments=arguments):
                result = pager(
                    "/my/orders?tag=a&tag=b#results",
                    total=60,
                    page=2,
                    url_args=arguments,
                )
                _logger.debug("Pager without new arguments: %s", result["page"])
                self.assertEqual(
                    result["page"]["url"],
                    "/my/orders/page/2?tag=a&tag=b#results",
                )

    def test_pager_functionality(self):
        test_cases = [
            {"total": 20, "page": 1, "expected_pages": [1]},
            {"total": 50, "page": 1, "expected_pages": [1, 2]},
            {"total": 150, "page": 3, "expected_pages": [1, 2, 3, 4, 5]},
            {"total": 300, "page": 5, "expected_pages": [1, "…", 4, 5, 6, "…", 10]},
            {"total": 300, "page": 1, "expected_pages": [1, 2, 3, 4, "…", 10]},
            {"total": 300, "page": 10, "expected_pages": [1, "…", 7, 8, 9, 10]},
        ]
        for case in test_cases:
            result = pager(
                url=case.get("url", "/test"),
                total=case["total"],
                page=case["page"],
                step=30,
                scope=5,
                url_args=None,
            )

            expected_page_count = (case["total"] + 30 - 1) // 30
            pages = [p["num"] for p in result["pages"]]

            with self.subTest(case=case):
                self.assertEqual(
                    pages,
                    case["expected_pages"],
                    f"Expected pages mismatch for case: {case}",
                )
                self.assertEqual(
                    result["page"]["num"],
                    case["page"],
                    f"Current page mismatch for case: {case}",
                )
                self.assertEqual(
                    result["page_count"],
                    expected_page_count,
                    f"Page count mismatch for case: {case}",
                )

    def test_pager_scope_is_honoured(self):
        common = {"url": "/test", "total": 300, "page": 5, "step": 30}
        cases = [
            (3, [1, "…", 5, "…", 10]),
            (5, [1, "…", 4, 5, 6, "…", 10]),
            (7, [1, 2, 3, 4, 5, 6, "…", 10]),
        ]
        for scope, expected in cases:
            with self.subTest(scope=scope):
                pages = [p["num"] for p in pager(**common, scope=scope)["pages"]]
                self.assertEqual(pages, expected)

    def test_pager_scope_below_minimum_does_not_degenerate(self):
        pages = [
            p["num"]
            for p in pager("/test", total=300, page=5, step=30, scope=1)["pages"]
        ]
        self.assertIn(5, pages)
        self.assertEqual(pages[0], 1)
        self.assertEqual(pages[-1], 10)

# Part of Odoo. See LICENSE file for full copyright and licensing details.
# FIXME temporary solution to patch wkhtmltopdf. It will need to be generalized
from contextlib import contextmanager, ExitStack
from unittest.mock import patch

from odoo.tests.common import HttpCase, release_test_lock, TransactionCase, TEST_CURSOR_COOKIE_NAME
from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.base_report_engine_wkhtmltox.models import ir_actions_report


class TransactionCaseWithPdf(TransactionCase):

    @contextmanager
    def allow_pdf_render(self):
        """
        Allows wkhtmltopdf to send requests to the backend.
        Enters registry mode if necessary.
        """
        with ExitStack() as stack:
            if not type(self)._registry_patched:
                stack.enter_context(self.enter_registry_test_mode())
            old_run_wkhtmltopdf = ir_actions_report._run_wkhtmltopdf

            def _patched_run_wkhtmltopdf(args):
                with patch.object(self, 'http_request_key', 'wkhtmltopdf'), release_test_lock():
                    args = ['--cookie', TEST_CURSOR_COOKIE_NAME, 'wkhtmltopdf', *args]
                    return old_run_wkhtmltopdf(args)

            stack.enter_context(
                patch.object(ir_actions_report, '_run_wkhtmltopdf', _patched_run_wkhtmltopdf)
            )
            yield


class HttpCaseWithPdf(HttpCase):

    def setUp(self):
        super().setUp()
        # we need to allow requests during pdf rendering.
        old_run_wkhtmltopdf = ir_actions_report._run_wkhtmltopdf

        def _patched_run_wkhtmltopdf(args):
            with patch.object(self, 'http_request_key', 'wkhtmltopdf'), release_test_lock():
                args = ['--cookie', TEST_CURSOR_COOKIE_NAME, 'wkhtmltopdf', *args]
                return old_run_wkhtmltopdf(args)

        self.startPatcher(
            patch.object(ir_actions_report, '_run_wkhtmltopdf', _patched_run_wkhtmltopdf),
        )

    @contextmanager
    def allow_pdf_render(self):
        """
        Allows wkhtmltopdf to send requests to the backend.
        Enters registry mode if necessary.
        """
        with ExitStack() as stack:
            if not type(self)._registry_patched:
                stack.enter_context(self.enter_registry_test_mode())
            old_run_wkhtmltopdf = ir_actions_report._run_wkhtmltopdf

            def _patched_run_wkhtmltopdf(args):
                with patch.object(self, 'http_request_key', 'wkhtmltopdf'), release_test_lock():
                    args = ['--cookie', TEST_CURSOR_COOKIE_NAME, 'wkhtmltopdf', *args]
                    return old_run_wkhtmltopdf(args)

            stack.enter_context(
                patch.object(ir_actions_report, '_run_wkhtmltopdf', _patched_run_wkhtmltopdf)
            )
            yield


class BaseCommonWithPdf(BaseCommon):

    @contextmanager
    def allow_pdf_render(self):
        """
        Allows wkhtmltopdf to send requests to the backend.
        Enters registry mode if necessary.
        """
        with ExitStack() as stack:
            if not type(self)._registry_patched:
                stack.enter_context(self.enter_registry_test_mode())
            old_run_wkhtmltopdf = ir_actions_report._run_wkhtmltopdf

            def _patched_run_wkhtmltopdf(args):
                with patch.object(self, 'http_request_key', 'wkhtmltopdf'), release_test_lock():
                    args = ['--cookie', TEST_CURSOR_COOKIE_NAME, 'wkhtmltopdf', *args]
                    return old_run_wkhtmltopdf(args)

            stack.enter_context(
                patch.object(ir_actions_report, '_run_wkhtmltopdf', _patched_run_wkhtmltopdf)
            )
            yield

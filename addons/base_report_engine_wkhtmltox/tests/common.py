# Part of Odoo. See LICENSE file for full copyright and licensing details.
from contextlib import contextmanager, ExitStack
from unittest.mock import patch

from odoo.addons.base.tests.common import BaseCommon
from odoo.tests.common import HttpCase, release_test_lock, TransactionCase, TEST_CURSOR_COOKIE_NAME
from odoo.addons.base_report_engine_wkhtmltox.models import ir_actions_report


# Tests can monkeypatch this in this module to emulate another backend key.
WKHTML_TEST_ENGINE = 'wkhtmltopdf'


def _patch_wkhtml_runner(case):
    old_run_wkhtmltopdf = ir_actions_report._run_wkhtmltopdf

    def _patched_run_wkhtmltopdf(args):
        with patch.object(case, 'http_request_key', WKHTML_TEST_ENGINE), release_test_lock():
            args = ['--cookie', TEST_CURSOR_COOKIE_NAME, WKHTML_TEST_ENGINE, *args]
            return old_run_wkhtmltopdf(args)

    return patch.object(ir_actions_report, '_run_wkhtmltopdf', _patched_run_wkhtmltopdf)


class _AllowPdfRenderMixin:

    @contextmanager
    def allow_pdf_render(self):
        """
        Allows wkhtmltopdf to send requests to the backend.
        Enters registry mode if necessary.
        """
        with ExitStack() as stack:
            if not type(self)._registry_patched:
                stack.enter_context(self.enter_registry_test_mode())
            stack.enter_context(_patch_wkhtml_runner(self))
            yield


class HttpCaseWithPdf(_AllowPdfRenderMixin, HttpCase):

    def setUp(self):
        super().setUp()
        # we need to allow requests during pdf rendering.
        self.startPatcher(_patch_wkhtml_runner(self))


class BaseCommonWithPdf(_AllowPdfRenderMixin, BaseCommon):
    pass

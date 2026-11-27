# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
from unittest.mock import patch

from odoo.tests.common import TransactionCase
from odoo.tools.pdf import PdfFileReader

from odoo.addons.base.models.ir_actions_report import ReportDocument, ReportPageSetup
from odoo.addons.base_report_wkhtmltox.models.ir_actions_report import IrActionsReport, _wkhtml


class TestWkhtmltopdfArgs(TransactionCase):
    def test_build_wkhtmltopdf_args(self):
        page_setup = ReportPageSetup(
            paper_format='A4',
            landscape=True,
            margin_top=0.0,
            margin_bottom=0.0,
            margin_left=50.0,
            margin_right=12.5,
            header_spacing=0.0,
            dpi=96,
        )
        command_args = self.env['ir.actions.report']._build_wkhtmltopdf_args(page_setup)
        self.assertEqual(command_args, [
            '--disable-local-file-access',
            '--quiet',
            '--page-size', 'A4',
            '--margin-top', '0',
            '--margin-bottom', '0',
            '--margin-left', '50',
            '--margin-right', '12.5',
            '--header-spacing', '0',
            '--dpi', '96',
            '--zoom', '1.0',
            '--orientation', 'landscape',
            '--javascript-delay', '1000',
        ])

    def test_build_wkhtmltopdf_args_custom_size(self):
        page_setup = ReportPageSetup(
            paper_format=None, page_width=100.0, page_height=50.0,
            header_line=True, disable_shrinking=True,
        )
        command_args = self.env['ir.actions.report']._build_wkhtmltopdf_args(page_setup)
        self.assertNotIn('--page-size', command_args)
        self.assertEqual(command_args[command_args.index('--page-width') + 1], '100mm')
        self.assertEqual(command_args[command_args.index('--page-height') + 1], '50mm')
        self.assertEqual(command_args[command_args.index('--orientation') + 1], 'portrait')
        self.assertIn('--header-line', command_args)
        self.assertIn('--disable-smart-shrinking', command_args)


class TestWkhtmltopdfDocuments(TransactionCase):
    def setUp(self):
        super().setUp()
        if _wkhtml().state != 'ok' or not _wkhtml().is_patched_qt:
            self.skipTest("Rendering multiple documents requires a working wkhtmltopdf with patched QT")
        self.runs = []
        run = IrActionsReport._run_wkhtmltopdf__

        def spy_run(self_report, args):
            self.runs.append(args)
            return run(self_report, args)

        self.startPatcher(patch.object(IrActionsReport, '_run_wkhtmltopdf__', spy_run))

    def _render(self, documents, page_setup):
        pdf = self.env['ir.actions.report']._run_pdf_engine_with_documents('wkhtmltopdf', documents, page_setup)
        return PdfFileReader(io.BytesIO(pdf)).pages

    def test_render_documents_with_own_headers(self):
        """ Each document gets its own header. """
        pages = self._render([
            ReportDocument(
                body=f'<html><body><p>Body {name}</p></body></html>',
                header=f'<!DOCTYPE html><html><body><p>Header {name}</p></body></html>',
            )
            for name in 'AB'
        ], ReportPageSetup(margin_top=30.0, header_spacing=5.0))
        self.assertEqual(len(self.runs), 1)
        self.assertEqual(self.runs[0].count('--header-html'), 2)
        self.assertEqual(len(pages), 2)
        for page, name, other in zip(pages, 'AB', 'BA'):
            text = page.extract_text()
            self.assertIn(f'Header {name}', text)
            self.assertNotIn(f'Header {other}', text)

    def test_render_documents_with_shared_header(self):
        """ Documents with the same header share its file. """
        header = '<!DOCTYPE html><html><body><p>Shared header</p></body></html>'
        pages = self._render([
            ReportDocument(body=f'<html><body><p>Body {name}</p></body></html>', header=header)
            for name in 'AB'
        ], ReportPageSetup(margin_top=30.0, header_spacing=5.0, landscape=True))
        args = self.runs[0]
        header_paths = {args[i + 1] for i, arg in enumerate(args) if arg == '--header-html'}
        self.assertEqual(args.count('--header-html'), 2)
        self.assertEqual(len(header_paths), 1)
        self.assertEqual(len(pages), 2)
        for page in pages:
            self.assertIn('Shared header', page.extract_text())
            self.assertGreater(page.mediabox.width, page.mediabox.height)

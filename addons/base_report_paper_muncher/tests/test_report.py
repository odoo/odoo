# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.tests import patch
from odoo.tests.common import TEST_CURSOR_COOKIE_NAME, release_test_lock
from odoo.tools import parse_version

from odoo.addons.base_report_paper_muncher.paper_muncher import (
    SERVE_TIMEOUT,
    PaperMuncherInfo,
    PaperMuncherServer,
    _capabilities,
    paper_muncher,
)


@odoo.tests.tagged('post_install', '-at_install')
class TestPaperMuncherReport(odoo.tests.HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env['ir.actions.report'].create({
            'name': 'Test Paper Muncher Report',
            'model': 'res.partner',
            'report_name': 'base_report_paper_muncher.test_report_partner',
            'report_type': 'qweb-pdf-paper-muncher',
            'paperformat_id': cls.env.ref('base.paperformat_euro').id,
        })
        cls.report_view = cls.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'base_report_paper_muncher.test_report_partner',
            'key': 'base_report_paper_muncher.test_report_partner',
            'arch': '''
                <t t-name="base_report_paper_muncher.test_report_partner">
                    <t t-call="web.html_container">
                        <t t-foreach="docs" t-as="o">
                            <div class="article">
                                <div class="page">
                                    <p>Name: <t t-out="o.name"/></p>
                                </div>
                            </div>
                        </t>
                    </t>
                </t>
            ''',
        })
        cls.partners = cls.env['res.partner'].create([
            {'name': 'PM Test Partner 1'},
            {'name': 'PM Test Partner 2'},
        ])

    def setUp(self):
        super().setUp()
        if paper_muncher().state != 'ok':
            self.skipTest("paper-muncher binary not found")

        # Mirror what HttpCase does for _run_wkhtmltopdf: set the test cursor key,
        # release the registry lock so _handle_fallback can open a TestCursor, and
        # inject the matching cookie into every fallback environ so Odoo's asset
        # routes pass assertCanOpenTestCursor.
        self_setup = self
        old_serve = PaperMuncherServer.serve

        def patched_serve_paper_muncher(self_server, documents, header='', footer='', *, timeout=SERVE_TIMEOUT):
            test_cookie = f'{TEST_CURSOR_COOKIE_NAME}=paper-muncher'
            if 'HTTP_COOKIE' in self_server._wsgi_environ:
                self_server._wsgi_environ['HTTP_COOKIE'] += f', {test_cookie}'
            else:
                self_server._wsgi_environ['HTTP_COOKIE'] = test_cookie

            with (
                patch.object(self_setup, 'http_request_key', 'paper-muncher'),
                release_test_lock(),
                patch('odoo.tests.common._disable_flushing_cursor', True),
            ):
                return old_serve(self_server, documents, header, footer, timeout=timeout)

        self.startPatcher(patch.object(
            PaperMuncherServer,
            'serve',
            patched_serve_paper_muncher,
        ))

    def _render_pdf(self, partner_ids):
        return self.env['ir.actions.report'].with_context(
            force_report_rendering=True,
        )._render_qweb_pdf(self.report, partner_ids)[0]

    def test_render_single_document(self):
        pdf = self._render_pdf([self.partners[0].id])
        self.assertTrue(pdf.startswith(b'%PDF-'), f"Expected a valid PDF got:\n{pdf}")

    def test_render_multiple_documents(self):
        pdf = self._render_pdf(self.partners.ids)
        self.assertTrue(pdf.startswith(b'%PDF-'), f"Expected a valid PDF got:\n{pdf}")

    def _render_pdf_with_headers(self):
        self.report_view.arch = '''
            <t t-name="base_report_paper_muncher.test_report_partner">
                <t t-call="web.html_container">
                    <t t-foreach="docs" t-as="o">
                        <div class="header"><p>Header: <t t-out="o.name"/></p></div>
                        <div class="article">
                            <div class="page">
                                <p>Name: <t t-out="o.name"/></p>
                            </div>
                        </div>
                        <div class="footer"><p>Footer: <t t-out="o.name"/></p></div>
                    </t>
                </t>
            </t>
        '''
        served = {}
        serve = PaperMuncherServer.serve

        def spy_serve(self_server, documents, header='', footer='', **kwargs):
            served.update(header=header, footer=footer)
            return serve(self_server, documents, header, footer, **kwargs)

        with patch.object(PaperMuncherServer, 'serve', spy_serve):
            pdf = self._render_pdf(self.partners.ids)
        self.assertTrue(pdf.startswith(b'%PDF-'), f"Expected a valid PDF got:\n{pdf}")
        return served

    def test_render_multiple_documents_with_headers(self):
        if not paper_muncher().has_capability('per-input-decoration'):
            self.skipTest("paper-muncher does not support per-input headers and footers")
        served = self._render_pdf_with_headers()
        for decoration in ('header', 'footer'):
            self.assertEqual(len(served[decoration]), 2)
            for document, partner, other in zip(served[decoration], self.partners, self.partners[::-1]):
                self.assertIn(partner.name, document)
                self.assertNotIn(other.name, document)

    def test_render_multiple_documents_with_headers_legacy(self):
        info = paper_muncher()
        legacy = info._replace(capabilities=info.capabilities - {'per-input-decoration'})
        with patch('odoo.addons.base_report_paper_muncher.models.ir_actions_report.paper_muncher', return_value=legacy):
            served = self._render_pdf_with_headers()
        self.assertIsInstance(served['header'], str)
        self.assertIsInstance(served['footer'], str)

    def test_capabilities(self):
        self.assertEqual(_capabilities(parse_version('0.5')), frozenset())
        self.assertEqual(_capabilities(parse_version('0.6')), {'baseline'})
        self.assertEqual(_capabilities(parse_version('0.10')), {
            'baseline',
            'per-input-decoration',
            'wkhtmltopdf-media-zero-viewport',
            'wkhtmltopdf-media-screen',
        })

    def test_capability_features(self):
        info = PaperMuncherInfo('ok', 'pm', (), capabilities=frozenset({'baseline', 'wkhtmltopdf-media-screen'}))
        self.assertEqual(info.features, ['wkhtmltopdf-quirks-media-screen'])

    def _render_pdf_args(self, info=None):
        started = {}
        init = PaperMuncherServer.__init__

        def spy_init(self_server, args, *a, **kw):
            started['args'] = [str(arg) for arg in args]
            init(self_server, args, *a, **kw)

        with patch.object(PaperMuncherServer, '__init__', spy_init), \
             patch.dict('os.environ', {'ODOO_PAPER_MUNCHER_FEATURE': ''}):
            if info:
                with patch('odoo.addons.base_report_paper_muncher.models.ir_actions_report.paper_muncher', return_value=info):
                    pdf = self._render_pdf(self.partners.ids)
            else:
                pdf = self._render_pdf(self.partners.ids)
        self.assertTrue(pdf.startswith(b'%PDF-'), f"Expected a valid PDF got:\n{pdf}")
        return started['args']

    def test_wkhtmltopdf_quirks_enabled_when_available(self):
        if not paper_muncher().has_capability('wkhtmltopdf-media-zero-viewport'):
            self.skipTest("paper-muncher has no wkhtmltopdf quirks")
        args = self._render_pdf_args()
        self.assertEqual(args.count('--feature'), 1)
        self.assertIn('wkhtmltopdf-quirks-media-zero-viewport=on', args)
        self.assertIn('wkhtmltopdf-quirks-media-screen=on', args)

    def test_wkhtmltopdf_quirks_not_passed_to_older_binaries(self):
        info = paper_muncher()
        legacy = info._replace(capabilities=info.capabilities - {
            'wkhtmltopdf-media-zero-viewport',
            'wkhtmltopdf-media-screen',
        })
        self.assertNotIn('--feature', self._render_pdf_args(legacy))

    def _scale_arg(self, args):
        return float(args[args.index('--scale') + 1].removesuffix('x'))

    def test_scale_smart_shrinking(self):
        paperformat = self.env.ref('base.paperformat_euro')
        self.assertFalse(paperformat.disable_shrinking)
        args = self._render_pdf_args()
        self.assertAlmostEqual(self._scale_arg(args), 76 / paperformat.dpi)

    def test_scale_disable_shrinking(self):
        paperformat = self.env.ref('base.paperformat_euro').copy({'disable_shrinking': True})
        self.report.paperformat_id = paperformat
        args = self._render_pdf_args()
        self.assertAlmostEqual(self._scale_arg(args), 96 / paperformat.dpi)

    def test_sandboxed(self):
        self.assertIn('--sandboxed', self._render_pdf_args())

    def test_split_decoration_mismatch(self):
        html = '<!DOCTYPE html><html><body><div id="minimal_layout_report_headers"><div>A</div><div>B</div></div></body></html>'
        split = self.env['ir.actions.report']._split_paper_muncher_decoration
        self.assertEqual(len(split(html, 'minimal_layout_report_headers', 2)), 2)
        self.assertIsNone(split(html, 'minimal_layout_report_headers', 3))
        self.assertIsNone(split(html, 'minimal_layout_report_footers', 2))
        self.assertIsNone(split(None, 'minimal_layout_report_headers', 2))

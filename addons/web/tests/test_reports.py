import io
import tempfile
from unittest.mock import Mock, patch

import odoo.tests
from odoo.exceptions import UserError
from odoo.http.session import session_store
from odoo.tests import no_retry, tagged
from odoo.tools import mute_logger
from odoo.tools.pdf import PdfReader

from odoo.addons.base.tests.files import PNG_RAW
from odoo.addons.http_routing.tests.common import MockRequest


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestReports(odoo.tests.HttpCase):
    def test_report_session_cookie(self):
        """ Asserts wkhtmltopdf forwards the user session when requesting resources to Odoo, such as images,
        and that the resource is correctly returned as expected.
        """
        partner_id = self.env.user.partner_id.id
        image = self.env['ir.attachment'].create({
            'name': 'foo',
            'res_model': 'res.partner',
            'res_id': partner_id,
            'raw': PNG_RAW,
        })
        report = self.env['ir.actions.report'].create({
            'name': 'test report',
            'report_name': 'base.test_report',
            'model': 'res.partner',
        })
        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'base.test_report',
            'key': 'base.test_report',
            'arch': f'''
                <main>
                    <div class="article" data-oe-model="res.partner" t-att-data-oe-id="docs.id">
                        <img src="/web/image/{image.id}"/>
                    </div>
                </main>
            '''
        })

        result = {}
        origin_find_record = self.env.registry['ir.binary']._find_record

        def _find_record(self, xmlid=None, res_model='ir.attachment', res_id=None, access_token=None, field=None):
            if res_model == 'ir.attachment' and res_id == image.id:
                result['uid'] = self.env.uid
                record = origin_find_record(self, xmlid, res_model, res_id, access_token, field)
                result.update({'record_id': record.id, 'data': record.raw.content or None})
            else:
                record = origin_find_record(self, xmlid, res_model, res_id, access_token, field)
            return record

        self.patch(self.env.registry['ir.binary'], '_find_record', _find_record)

        # 1. Request the report as admin, who has access to the image
        admin = self.env.ref('base.user_admin')
        admin_device_log_count_before = self.env['res.device.log'].search_count([('user_id', '=', admin.id)])
        report = report.with_user(admin)
        with MockRequest(report.env) as mock_request:
            mock_request.session = self.authenticate(admin.login, admin.login)
            report.with_context(force_report_rendering=True)._render_qweb_pdf(report.id, [partner_id])
        # Check that no device logs have been generated
        admin_device_log_count_after = self.env['res.device.log'].search_count([('user_id', '=', admin.id)])
        self.assertFalse(admin_device_log_count_after - admin_device_log_count_before)

        self.assertEqual(
            result.get('uid'), admin.id, 'wkhtmltopdf is not fetching the image as the user printing the report'
        )
        self.assertEqual(result.get('record_id'), image.id, 'wkhtmltopdf did not fetch the expected record')
        self.assertEqual(result.get('data'), PNG_RAW, 'wkhtmltopdf did not fetch the right image content')

        # 2. Request the report as public, who has no acess to the image
        self.logout()
        result.clear()
        public = self.env.ref('base.public_user')
        public_device_log_count_before = self.env['res.device.log'].search_count([('user_id', '=', public.id)])
        report = report.with_user(public)
        with MockRequest(self.env) as mock_request:
            mock_request.session = self.authenticate(None, None)
            report.with_context(force_report_rendering=True)._render_qweb_pdf(report.id, [partner_id])
        # Check that no device logs have been generated
        public_device_log_count_after = self.env['res.device.log'].search_count([('user_id', '=', public.id)])
        self.assertFalse(public_device_log_count_after - public_device_log_count_before)

        self.assertEqual(
            result.get('uid'), public.id, 'wkhtmltopdf is not fetching the image as the user printing the report'
        )
        self.assertEqual(result.get('record_id'), None, 'wkhtmltopdf must not have been allowed to fetch the image')
        self.assertEqual(result.get('data'), None, 'wkhtmltopdf must not have been allowed to fetch the image')

    def test_report_icon_is_a_glyph(self):
        """An icon must reach a PDF report as a glyph, never as its own name.

        Three things must line up: wkhtmltopdf must be able to load the icon
        font, `font-family` must survive the stylesheet, and the ligature turning
        the icon name into a glyph must be applied. Each of them silently prints
        the icon name (or nothing) in the middle of the report when it fails.
        """
        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'base.test_report',
            'key': 'base.test_report',
            'arch': '''
                <t t-call="web.basic_layout">
                    <i class="oi" data-icon="phone"/>
                    <i class="oi" data-icon="oi_view-kanban"/>
                </t>
            ''',
        })
        report = self.env['ir.actions.report'].create({
            'name': 'test report',
            'report_name': 'base.test_report',
            'model': 'res.partner',
        })
        admin = self.env.ref('base.user_admin')
        report = report.with_user(admin)
        with MockRequest(report.env) as mock_request:
            mock_request.session = self.authenticate(admin.login, admin.login)
            pdf, _report_type = report.with_context(force_report_rendering=True)._render_qweb_pdf(
                report.id, [admin.partner_id.id],
            )

        page = PdfReader(io.BytesIO(pdf)).pages[0]
        fonts = page['/Resources'].get_object().get('/Font') or {}
        base_fonts = {str(font.get_object().get('/BaseFont')) for font in fonts.values()}
        for font_name in ('MaterialSymbols', 'odoo_ui_icons'):
            self.assertTrue(
                any(font_name in base_font for base_font in base_fonts),
                f"the {font_name} font is missing from the report, which embeds only {sorted(base_fonts)}: "
                f"the engine could not load the font, or dropped the `font-family` naming it",
            )
        self.assertNotIn(
            'phone', page.extract_text(),
            "the icon name was printed as text instead of being replaced by its glyph: "
            "the font loaded, but its ligatures were not applied",
        )

    @mute_logger('odoo.addons.base_report_wkhtmltox.models.ir_actions_report')
    @no_retry
    def test_report_error_cleanup(self):
        admin = self.env.ref('base.user_admin')
        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'base.test_report',
            'key': 'base.test_report',
            'arch': '''
                <main>
                    <div>
                        <p>TEST</p>
                    </div>
                </main>
            '''
        })
        report = self.env['ir.actions.report'].create({
            'name': 'test report',
            'report_name': 'base.test_report',
            'model': 'res.partner',
        })
        report = report.with_user(admin)

        with (MockRequest(report.env) as mock_request,
            patch('subprocess.run') as mock_popen,
            patch.object(session_store(), 'delete') as mock_delete,
            patch('tempfile._TemporaryFileCloser.cleanup', autospec=True, wraps=tempfile._TemporaryFileCloser.cleanup) as mock_unlink):

            mock_request.session = self.authenticate(admin.login, admin.login)

            mock_process = Mock()
            mock_process.returncode = -1
            mock_process.stderr = ""
            mock_popen.return_value = mock_process

            with self.assertRaises(UserError):
                report.with_context(force_report_rendering=True)._render_qweb_pdf(report.id)

            # Check if the temporary session has been deleted
            self.assertEqual(mock_delete.call_count, 1)
            self.assertNotEqual(mock_delete.call_args.args[0].sid, mock_request.session.sid)

            # Check if temporary files have been deleted
            deleted_files = ''.join([call.args[0].name for call in mock_unlink.call_args_list])
            self.assertIn('report.cookie_jar.tmp', deleted_files)
            self.assertIn('report.header.tmp', deleted_files)
            self.assertIn('report.footer.tmp', deleted_files)
            self.assertIn('report.body.tmp', deleted_files)
            self.assertIn('report.tmp', deleted_files)

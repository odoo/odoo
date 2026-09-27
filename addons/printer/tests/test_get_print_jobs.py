import base64
from io import BytesIO
from unittest.mock import patch
from xml.etree import ElementTree as ET

from PIL import Image

from odoo.tests import TransactionCase


def make_png_bytes(width=100, height=200) -> bytes:
    buf = BytesIO()
    Image.new("RGB", (width, height), color=128).save(buf, format="PNG")
    return buf.getvalue()


class TestGetPrintJobs(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.report = cls.env.ref('base.ir_module_reference_print')
        cls.doc = cls.env.ref('base.module_base')

    def _link_printer(self, printer_type):
        printer = self.env['printer.printer'].create({
            'name': f'Test {printer_type}',
            'ip_address': '127.0.0.1',
            'type': printer_type,
        })
        self.report.printer_ids = [(6, 0, printer.ids)]
        return printer

    def test_epos_job_built_from_qweb_pdf_report(self):
        """A qweb-pdf report linked to an ePOS printer must be rendered to an
        image (html -> wkhtmltoimage -> thermal_printer_format) and returned as
        an 'epos' job, without needing any dedicated ePOS template."""
        self._link_printer('epos')
        with patch(
            'odoo.addons.base_report_wkhtmltox.models.ir_actions_report.IrActionsReport._run_image_engine',
            return_value=[make_png_bytes()],
        ) as run_image_engine:
            jobs = self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})

        self.assertTrue(run_image_engine.called)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0]['type'], 'epos')
        xml = base64.b64decode(jobs[0]['report']).decode()
        ET.fromstring(xml)
        self.assertIn('<image', xml)
        self.assertIn('<cut type="feed"', xml)

    def test_no_job_without_linked_epos_printer(self):
        jobs = self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        self.assertEqual(jobs, [])

    def test_no_job_when_image_rendering_fails(self):
        self._link_printer('epos')
        with patch(
            'odoo.addons.base_report_wkhtmltox.models.ir_actions_report.IrActionsReport._run_image_engine',
            return_value=[None],
        ):
            jobs = self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        self.assertEqual(jobs, [])

    def test_non_pdf_report_not_rendered_as_image_even_with_epos_printer(self):
        """Only qweb-pdf reports go through the image path; a qweb-text report
        linked to an ePOS printer must not trigger it."""
        self.report.report_type = 'qweb-text'
        self._link_printer('epos')
        with patch(
            'odoo.addons.base_report_wkhtmltox.models.ir_actions_report.IrActionsReport._run_image_engine',
        ) as run_image_engine:
            self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        run_image_engine.assert_not_called()

    def test_epos_html_gets_a_base_href(self):
        """Relative URLs (e.g. the barcode widget's <img src="/report/barcode/...">)
        only resolve for wkhtmltoimage if the standalone HTML carries a <base href>,
        since wkhtmltoimage renders it as an isolated local file with no page URL
        of its own to resolve relative paths against."""
        self._link_printer('epos')
        base_url = self.report._get_report_url()
        with patch(
            'odoo.addons.base_report_wkhtmltox.models.ir_actions_report.IrActionsReport._run_image_engine',
        ) as run_image_engine:
            run_image_engine.return_value = [make_png_bytes()]
            self.report.get_print_jobs(self.report.report_name, self.doc.ids, {})
        rendered_html = run_image_engine.call_args.args[1][0]
        self.assertIn(f'<head><base href="{base_url}"/>', rendered_html)

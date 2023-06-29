# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from base64 import b64decode

import odoo
import odoo.tests


_logger = logging.getLogger(__name__)


@odoo.tests.tagged('post_install', '-at_install', 'post_install_l10n')
class TestReports(odoo.tests.TransactionCase):
    def test_reports(self):
        invoice_domain = [('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt', 'in_invoice', 'in_refund', 'in_receipt'))]
        specific_model_domains = {
            'account.report_original_vendor_bill': [('move_type', 'in', ('in_invoice', 'in_receipt'))],
            'account.report_invoice_with_payments': invoice_domain,
            'account.report_invoice': invoice_domain,
            'l10n_th.report_commercial_invoice': invoice_domain,
        }
        Report = self.env['ir.actions.report']
        for report in Report.search([('report_type', 'like', 'qweb')]):
            report_model = 'report.%s' % report.report_name
            try:
                self.env[report_model]
            except KeyError:
                # Only test the generic reports here
                _logger.info("testing report %s", report.report_name)
                report_model_domain = specific_model_domains.get(report.report_name, [])
                report_records = self.env[report.model].search(report_model_domain, limit=10)
                if not report_records:
                    _logger.info("no record found skipping report %s", report.report_name)

                # Test report generation
                if not report.multi:
                    for record in report_records:
                        Report._render_qweb_html(report.id, record.ids)
                else:
                    Report._render_qweb_html(report.id, report_records.ids)
            else:
                continue

    def test_report_reload_from_attachment(self):
        def get_attachments(res_id):
            return self.env["ir.attachment"].search([('res_model', "=", "res.partner"), ("res_id", "=", res_id)])

        Report = self.env['ir.actions.report'].with_context(force_report_rendering=True)

        report = Report.create({
            'name': 'test report',
            'report_name': 'base.test_report',
            'model': 'res.partner',
        })

        self.env['ir.ui.view'].create({
            'type': 'qweb',
            'name': 'base.test_report',
            'key': 'base.test_report',
            'arch': '''
                <main>
                    <div class="article" data-oe-model="res.partner" t-att-data-oe-id="docs.id">
                        <span t-field="docs.display_name" />
                    </div>
                </main>
            '''
        })

        pdf_text = "0"
        def _run_wkhtmltopdf(*args, **kwargs):
            return bytes(pdf_text, "utf-8")

        self.patch(type(Report), "_run_wkhtmltopdf", _run_wkhtmltopdf)

        # sanity check: the report is not set to save attachment
        # assert that there are no pre-existing attachment
        partner_id = self.env.user.partner_id.id
        self.assertFalse(get_attachments(partner_id))
        pdf = report._render_qweb_pdf(report.id, [partner_id])
        self.assertFalse(get_attachments(partner_id))
        self.assertEqual(pdf[0], b"0")

        # set the report to reload from attachment and make one
        pdf_text = "1"
        report.attachment = "'test_attach'"
        report.attachment_use = True
        report._render_qweb_pdf(report.id, [partner_id])
        attach_1 = get_attachments(partner_id)
        self.assertTrue(attach_1.exists())

        # use the context key to not reload from attachment
        # and not create another one
        pdf_text = "2"
        report = report.with_context(report_pdf_no_attachment=True)
        pdf = report._render_qweb_pdf(report.id, [partner_id])
        attach_2 = get_attachments(partner_id)
        self.assertEqual(attach_2.id, attach_1.id)

        self.assertEqual(b64decode(attach_1.datas), b"1")
        self.assertEqual(pdf[0], b"2")

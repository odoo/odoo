# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging

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


@odoo.tests.tagged('post_install', '-at_install')
class TestAggregatePdfReports(odoo.tests.HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partners = cls.env["res.partner"].create([{
            "name": "Rodion Romanovich Raskolnikov"
        }, {
            "name": "Dmitri Prokofich Razumikhin"
        }, {
            "name": "Porfiry Petrovich"
        }])

        cls.env["ir.actions.report"].create({
            "name": "test report",
            "report_name": "base.test_report",
            "model": "res.partner",
        })

    def test_aggregate_report_with_some_resources_reloaded_from_attachment(self):
        """
        Test for opw-3827700, which caused reports generated for multiple records to fail if there was a record in
        the middle that had an attachment, and 'Reload from attachment' was enabled for the report. The misbehavior was
        caused by an indexing issue.
        """
        self.env["ir.ui.view"].create({
            "type": "qweb",
            "name": "base.test_report",
            "key": "base.test_report",
            "arch": """
                    <main>
                        <div t-foreach="docs" t-as="user">
                            <div class="article" data-oe-model="res.partner" t-att-data-oe-id="user.id">
                                <span t-esc="user.display_name"/>
                            </div>
                        </div>
                    </main>
                    """
        })
        self.assert_report_creation("base.test_report", self.partners, self.partners[1])

    def test_aggregate_report_with_some_resources_reloaded_from_attachment_with_multiple_page_report(self):
        """
        Same as @test_report_with_some_resources_reloaded_from_attachment, but tests the behavior for reports that
        span multiple pages per record.
        """
        self.env["ir.ui.view"].create({
            "type": "qweb",
            "name": "base.test_report",
            "key": "base.test_report",
            "arch": """
                    <main>
                        <div t-foreach="docs" t-as="user">
                            <div class="article" data-oe-model="res.partner" t-att-data-oe-id="user.id" >
                                <!-- This headline helps report generation to split pdfs per record after it generates
                                     the report in bulk by creating an outline. -->
                                <h1>Name</h1>
                                <!-- Make this a multipage report. -->
                                <div t-foreach="range(100)" t-as="i">
                                    <span t-esc="i"/> - <span t-esc="user.display_name"/>
                                </div>
                            </div>
                        </div>
                    </main>
                    """
        })
        self.assert_report_creation("base.test_report", self.partners, self.partners[1])

    def assert_report_creation(self, report_ref, records, record_to_report):
        self.assertIn(record_to_report, records, "Record to report must be in records list")

        reports = self.env['ir.actions.report'].with_context(force_report_rendering=True)

        # Make sure attachments are created.
        report = reports._get_report(report_ref)
        if not report.attachment:
            report.attachment = "object.name + '.pdf'"
        report.attachment_use = True

        # Generate report for chosen record to create an attachment.
        record_report, content_type = reports._render_qweb_pdf(report_ref, res_ids=record_to_report.id)
        self.assertEqual(content_type, "pdf", "Report is not a PDF")
        self.assertTrue(record_report, "PDF not generated")

        # Make sure the attachment is created.
        report = reports._get_report(report_ref)
        self.assertTrue(report.retrieve_attachment(record_to_report), "Attachment not generated")

        aggregate_report_content, content_type = reports._render_qweb_pdf(report_ref, res_ids=records.ids)
        self.assertEqual(content_type, "pdf", "Report is not a PDF")
        self.assertTrue(aggregate_report_content, "PDF not generated")
        for record in records:
            self.assertTrue(report.retrieve_attachment(record), "Attachment not generated")

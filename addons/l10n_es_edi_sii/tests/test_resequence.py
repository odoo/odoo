from datetime import date

from freezegun import freeze_time

from odoo.exceptions import UserError
from odoo.tests import Form, tagged

from .common import TestEsEdiCommon, mocked_l10n_es_edi_call_web_service_sign


@tagged("post_install_l10n", "post_install", "-at_install")
class TestResequenceSII(TestEsEdiCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref='es_full', edi_format_ref='l10n_es_edi_sii.edi_es_sii'):
        cls.startClassPatcher(freeze_time("2019-06-01", tick=True))
        super().setUpClass(chart_template_ref=chart_template_ref, edi_format_ref=edi_format_ref)
        cls.classPatch(
            cls.registry["account.edi.format"],
            "_l10n_es_edi_call_web_service_sign",
            mocked_l10n_es_edi_call_web_service_sign,
        )
        # Create 2 customer and 2 vendor invoices, in wrong date order
        cls.customer_invoice_2 = cls.create_invoice(
            invoice_date="2019-05-15", date="2019-05-15", invoice_line_ids=[{}]
        )
        cls.customer_invoice_1 = cls.create_invoice(
            invoice_date="2019-05-01", date="2019-05-01", invoice_line_ids=[{}]
        )
        cls.vendor_invoice_2 = cls.create_invoice(
            invoice_date="2019-04-15",
            date="2019-04-15",
            move_type="in_invoice",
            ref="vendor/1",
            invoice_line_ids=[{}],
        )
        cls.vendor_invoice_1 = cls.create_invoice(
            invoice_date="2019-04-01",
            date="2019-04-01",
            move_type="in_invoice",
            ref="vendor/2",
            invoice_line_ids=[{}],
        )
        # Post them, in wrong date order
        cls.customer_invoice_2.action_post()
        cls.customer_invoice_1.action_post()
        cls.vendor_invoice_2.action_post()
        cls.vendor_invoice_1.action_post()

    def setUp(self):
        super().setUp()
        # Send to SII
        all_invoices = (
            self.customer_invoice_1
            + self.customer_invoice_2
            + self.vendor_invoice_1
            + self.vendor_invoice_2
        )
        self.generated_files = self._process_documents_web_services(
            all_invoices, {self.edi_format.code}
        )
        self.assertRecordValues(
            all_invoices,
            [
                {
                    "invoice_date": date(2019, 5, 1),
                    "date": date(2019, 5, 1),
                    "name": "INV/2019/00002",
                },
                {
                    "invoice_date": date(2019, 5, 15),
                    "date": date(2019, 5, 15),
                    "name": "INV/2019/00001",
                },
                {
                    "invoice_date": date(2019, 4, 1),
                    "date": date(2019, 4, 1),
                    "name": "BILL/2019/04/0002",
                },
                {
                    "invoice_date": date(2019, 4, 15),
                    "date": date(2019, 4, 15),
                    "name": "BILL/2019/04/0001",
                },
            ],
        )

    def test_customer_fails(self):
        """Check we cannot resequence customer invoices."""
        invoices = self.customer_invoice_1 + self.customer_invoice_2
        wiz_f = Form(
            self.env["account.resequence.wizard"].with_context(
                active_model="account.move",
                active_ids=invoices.ids,
            )
        )
        wiz_f.ordering = "date"
        wiz = wiz_f.save()
        with self.assertRaises(
            UserError,
            msg="The following documents have already been sent and cannot be resequenced: INV/2019/00001, INV/2019/00002",
        ):
            wiz.resequence()

    def test_vendor_works(self):
        """Check we can resequence vendor bills."""
        invoices = self.vendor_invoice_1 + self.vendor_invoice_2
        wiz_f = Form(
            self.env["account.resequence.wizard"].with_context(
                active_model="account.move",
                active_ids=invoices.ids,
            )
        )
        wiz_f.ordering = "date"
        wiz = wiz_f.save()
        wiz.resequence()
        self.assertRecordValues(
            invoices,
            [
                {
                    "invoice_date": date(2019, 4, 1),
                    "date": date(2019, 4, 1),
                    "name": "BILL/2019/04/0001",
                },
                {
                    "invoice_date": date(2019, 4, 15),
                    "date": date(2019, 4, 15),
                    "name": "BILL/2019/04/0002",
                },
            ],
        )

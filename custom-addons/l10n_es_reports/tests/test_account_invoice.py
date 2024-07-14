from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged, Form

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountInvoice(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref="es_pymes"):
        super().setUpClass(chart_template_ref=chart_template_ref)

    def setUp(self):
        super().setUp()
        self.account_revenue = self.env['account.account'].search(
            [('account_type', '=', 'income')], limit=1)
        self.company = self.env.user.company_id
        self.partner_es = self.env['res.partner'].create({
            'name': 'España',
            'country_id': self.env.ref('base.es').id,
        })
        self.partner_eu = self.env['res.partner'].create({
            'name': 'France',
            'country_id': self.env.ref('base.fr').id,
        })

    def create_invoice(self, partner_id):
        f = Form(self.env['account.move'].with_context(default_move_type="out_invoice"))
        f.partner_id = partner_id
        with f.invoice_line_ids.new() as line:
            line.product_id = self.env.ref("product.product_product_4")
            line.quantity = 1
            line.price_unit = 100
            line.name = 'something'
            line.account_id = self.account_revenue
        invoice = f.save()
        return invoice

    def test_mod347_default_include_domestic_invoice(self):
        invoice = self.create_invoice(self.partner_es)
        self.assertEqual(invoice.l10n_es_reports_mod347_invoice_type, 'regular')

    def test_mod347_exclude_intracomm_invoice(self):
        invoice = self.create_invoice(self.partner_eu)
        self.assertFalse(invoice.l10n_es_reports_mod347_invoice_type)

    @freeze_time('2019-12-31')
    def test_mod347_include_receipts(self):
        self.init_invoice(
            'out_receipt',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2019-12-31',
            post=True,
        )

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2019-12-31", "2019-12-31", default_options={"unfold_all": True}
        )

        lines = report._get_lines(options)
        lines = lines[1:3] + lines[-2:]
        self.assertLinesValues(
            lines,
            [0, 1],
            [
                ["Total number of persons and entities",                         1],
                ["España",                                                       1],
                ["B - Sales of goods and services greater than 3.005,06 €", 5000.0],
                ["España",                                                  5000.0],
            ],
            options,
        )

    @freeze_time('2019-12-31')
    def test_mod347_not_affected_by_payments(self):
        invoice = self.init_invoice(
            'out_invoice',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2019-12-31',
            post=True,
        )

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2019-12-31", "2019-12-31", default_options={"unfold_all": True}
        )

        expected_lines = [
            ["Total number of persons and entities",                         1],
            ["España",                                                       1],
            ["B - Sales of goods and services greater than 3.005,06 €", 5000.0],
            ["España",                                                  5000.0],
        ]

        lines = report._get_lines(options)
        lines = lines[1:3] + lines[-2:]
        self.assertLinesValues(
            lines,
            [0, 1],
            expected_lines,
            options,
        )

        self.env['account.payment.register'].with_context(
            active_ids=invoice.ids, active_model='account.move'
        ).create({})._create_payments()

        lines = report._get_lines(options)
        lines = lines[1:3] + lines[-2:]
        self.assertLinesValues(
            lines,
            [0, 1],
            expected_lines,
            options,
        )

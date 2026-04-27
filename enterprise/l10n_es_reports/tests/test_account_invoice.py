from odoo import fields

from odoo.addons.account_reports.tests.common import TestAccountReportsCommon
from odoo.tests import tagged, Form

from freezegun import freeze_time


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestAccountInvoice(TestAccountReportsCommon):
    @classmethod
    @TestAccountReportsCommon.setup_chart_template('es_pymes')
    def setUpClass(cls):
        super().setUpClass()

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
        ChartTemplate = self.env["account.chart.template"].with_company(self.company)
        self.tax_withhold_purchase = ChartTemplate.ref('account_tax_template_p_irpf15')
        self.tax_withhold_sale = ChartTemplate.ref('account_tax_template_s_irpf15')

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
                ["B - Sales of goods and services greater than 3,005.06 €", 5000.0],
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
            ["B - Sales of goods and services greater than 3,005.06 €", 5000.0],
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

    @freeze_time('2019-12-31')
    def test_mod347_journal_entry(self):
        """Test that a journal entry without partner will not alter mod347 report"""
        self.init_invoice(
            'out_invoice',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2019-12-31',
            post=True,
        )

        entry = self.env['account.move'].create({
            'move_type': 'entry',
            'line_ids': [
                (0, None, {
                    'name': 'revenue line',
                    'account_id': self.company_data['default_account_payable'].id,
                    'debit': 5000.0,
                    'credit': 0.0,
                }),
                (0, None, {
                    'name': 'counterpart line',
                    'account_id': self.company_data['default_account_receivable'].id,
                    'credit': 5000.0,
                    'debit': 0.0,
                }),
            ]
        })
        entry.l10n_es_reports_mod347_invoice_type = 'regular'
        entry.action_post()

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2019-12-31", "2019-12-31", default_options={"unfold_all": True}
        )

        expected_lines = [
            ["Total number of persons and entities",                         1],
            ["España",                                                       1],
            ["B - Sales of goods and services greater than 3,005.06 €", 5000.0],
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

    @freeze_time('2019-12-31')
    def test_vat_record_books_with_receipts(self):
        self.init_invoice(
            'out_receipt',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2019-12-31',
            taxes=self.company_data['default_tax_sale'],
            post=True,
        )
        receipt = self.init_invoice(
            'out_receipt',
            amounts=[3000],
            invoice_date='2019-12-31',
            taxes=self.company_data['default_tax_sale'],
        )
        receipt.partner_id = False
        receipt.action_post()

        report = self.env.ref('account.generic_tax_report')
        options = self._generate_options(
            report, "2019-12-31", "2019-12-31", default_options={"unfold_all": True}
        )

        vat_record_books = self.env['l10n_es.libros.registro.export.handler'].export_libros_de_iva(options)['file_content']

        self._test_xlsx_file(vat_record_books, {
            0: ('Autoliquidación', '', 'Actividad', '', '', 'Tipo de Factura', 'Concepto de Ingreso', 'Ingreso Computable', 'Fecha Expedición', 'Fecha Operación', 'Identificación de la Factura', '', '', 'NIF Destinario', '', '', 'Nombre Destinario', 'Clave de Operación', 'Calificación de la Operación', 'Operación Exenta', 'Total Factura', 'Base Imponible', 'Tipo de IVA', 'Cuota IVA Repercutida', 'Tipo de Recargo eq.', 'Cuota Recargo eq.', 'Cobro (Operación Criterio de Caja de IVA y/o artículo 7.2.1º de Reglamento del IRPF)', '', '', '', 'Tipo Retención del IRPF', 'Importe Retenido del IRPF', 'Registro Acuerdo Facturación', 'Inmueble', '', 'Referencia Externa'),
            1: ('Ejercicio', 'Periodo', 'Código', 'Tipo', 'Grupo o Epígrafe del IAE', '', '', '', '', '', 'Serie', 'Número', 'Número-Final', 'Tipo', 'Código País', 'Identificación', '', '', '', '', '', '', '', '', '', '', 'Fecha', 'Importe', 'Medio Utilizado', 'Identificación Medio Utilizado', '', '', '', 'Situación', 'Referencia Catastral', ''),
            2: (2019, '4T', 'A', '01', '0000', 'F2', 'I01', 3000, '31/12/2019', '', '', 'INV/2019/00002', '', '', '', '', False, '01', 'S1', '', 3630, 3000, 21, 630, 0, 0, '', '', '', '', 0, 0, '', '', '', ''),
            3: (2019, '4T', 'A', '01', '0000', 'F1', 'I01', 5000, '31/12/2019', '', '', 'INV/2019/00001', '', '', '', '', 'España', '01', 'S1', '', 6050, 5000, 21, 1050, 0, 0, '', '', '', '', 0, 0, '', '', '', ''),
        })

    def test_exclude_349_from_internal_customer_invoice(self):
        """
        Test that when creating an invoice for a spanish customer, l10n_es_reports_mod349_invoice_type is set to False
        also test that when creating an invoice for a european partner l10n_es_reports_mod349_invoice_type is set
        to its default value
        """
        invoice_es = self.init_invoice(
            'out_invoice',
            partner=self.partner_es,
            amounts=[10],
            post=True,
        )

        self.assertEqual(invoice_es.l10n_es_reports_mod347_invoice_type, 'regular')
        self.assertFalse(invoice_es.l10n_es_reports_mod349_invoice_type)

        partner_fr = self.env['res.partner'].create({
            'name': 'France',
            'country_id': self.env.ref('base.fr').id,
            'is_company': True,
        })
        invoice_eu = self.init_invoice(
            'out_invoice',
            partner=partner_fr,
            amounts=[10],
            post=True,
        )

        self.assertEqual(invoice_eu.l10n_es_reports_mod349_invoice_type, 'E')

    @freeze_time('2025-09-01')
    def test_mod347_withhold_tax(self):
        """
        Test that withholding taxes are excluded from the Modelo 347 report,
        unless overridden by the user via the l10n_es_reports_mod347_invoice_type field.
        """
        self.init_invoice('out_invoice', invoice_date=fields.Date.today(), partner=self.partner_es, amounts=[40000], taxes=[self.company_data['default_tax_sale'], self.tax_withhold_sale], post=True)
        self.init_invoice('out_invoice', invoice_date=fields.Date.today(), partner=self.partner_es.copy(), amounts=[2800], taxes=[self.company_data['default_tax_sale'], self.tax_withhold_sale], post=True)
        self.init_invoice('in_invoice', invoice_date=fields.Date.today(), partner=self.partner_es, amounts=[40000], taxes=[self.company_data['default_tax_purchase'], self.tax_withhold_purchase], post=True)
        insurance_bill = self.init_invoice('in_invoice', invoice_date=fields.Date.today(), partner=self.partner_es, amounts=[40000], taxes=[self.company_data['default_tax_purchase'], self.tax_withhold_purchase])
        insurance_bill.l10n_es_reports_mod347_invoice_type = 'insurance'
        insurance_bill.action_post()

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2025-01-31", "2025-12-31", default_options={"unfold_all": True}
        )

        expected_values = [
            ('Summary',                                                          ''),
            ('Total number of persons and entities',                              1),
            ('España',                                                            1),
            ('Insurance operations',                                             ''),
            ('A - Purchases of goods and services greater than 3,005.06 €', 48400.0),
            ('España',                                                      48400.0),
            ('Other operations',                                                 ''),
            ('A - Purchases of goods and services greater than 3,005.06 €',     0.0),
            ('B - Sales of goods and services greater than 3,005.06 €',         0.0),
        ]
        lines = report._get_lines(options)

        self.assertLinesValues(
            lines[0:3] + lines[-7:-4] + lines[-3:],
            [0, 1],
            expected_values,
            options,
        )

    def test_mod347_include_negative_threshold(self):
        self.init_invoice(
            'out_invoice',
            partner=self.partner_es,
            amounts=[4000],
            invoice_date='2025-11-25',
            post=True,
        )

        self.init_invoice(
            'out_refund',
            partner=self.partner_es,
            amounts=[10000],
            invoice_date='2025-11-25',
            post=True,
        )

        partner_es_2 = self.partner_es.copy()

        self.init_invoice(
            'in_invoice',
            partner=partner_es_2,
            amounts=[2000],
            invoice_date='2025-11-25',
            post=True,
        )

        self.init_invoice(
            'in_refund',
            partner=partner_es_2,
            amounts=[5500],
            invoice_date='2025-11-25',
            post=True,
        )

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2025-11-01", "2025-11-30", default_options={"unfold_all": True}
        )

        lines = report._get_lines(options)
        lines = lines[1:4] + lines[-5:]

        self.assertLinesValues(
            lines,
            [0, 1],
            [
                ("Total number of persons and entities",                              2),
                ("España",                                                            2),
                ("España (copy)",                                                     2),
                ('Other operations',                                                 ''),
                ('A - Purchases of goods and services greater than 3,005.06 €', -3500.0),
                ('España (copy)',                                               -3500.0),
                ("B - Sales of goods and services greater than 3,005.06 €",     -6000.0),
                ("España",                                                      -6000.0),
            ],
            options,
        )

    def test_mod347_separate_purchase_and_sale_thresholds(self):
        """
        Ensure Sales and Purchases are checked separately against the 3,005.06 € threshold.
        The partner must appear if either group exceeds the limit, even if they cancel
        each other out.
        """
        # 1. Create a Vendor Bill (Purchase) of 5,000 €
        self.init_invoice(
            'in_invoice',
            partner=self.partner_es,
            amounts=[5000],
            invoice_date='2025-11-27',
            post=True,
        )

        # 2. Create a Customer Credit Note (Sale Refund) of 7,000 €
        self.init_invoice(
            'out_refund',
            partner=self.partner_es,
            amounts=[7000],
            invoice_date='2025-11-27',
            post=True,
        )

        report = self.env.ref('l10n_es_reports.mod_347')
        options = self._generate_options(
            report, "2025-11-01", "2025-11-30", default_options={"unfold_all": True}
        )

        lines = report._get_lines(options)
        lines = lines[1:3] + lines[-5:]

        self.assertLinesValues(
            lines,
            [0, 1],
            [
                ("Total number of persons and entities",                             1),
                ("España",                                                           2),
                ('Other operations',                                                ''),
                ("A - Purchases of goods and services greater than 3,005.06 €", 5000.0),
                ("España",                                                      5000.0),
                ("B - Sales of goods and services greater than 3,005.06 €",    -7000.0),
                ("España",                                                     -7000.0),
            ],
            options,
        )

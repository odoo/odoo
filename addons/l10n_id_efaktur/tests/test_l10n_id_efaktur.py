import csv

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged, common
from odoo.addons.l10n_id_efaktur.models.account_move import FK_HEAD_LIST, LT_HEAD_LIST, OF_HEAD_LIST, _csv_row
from odoo.exceptions import RedirectWarning


@tagged('post_install', '-at_install', 'post_install_l10n')
class TestIndonesianEfaktur(common.TransactionCase):
    def setUp(self):
        """
        1) contact with l10n_id_pkp=True, l10n_id_kode_transaksi="01"
        2) tax: amount=10, type_tax_use=sale, price_include=True
        3) invoice with partner_id=contact, journal=customer invoices,
        """
        super().setUp()

        self.maxDiff = 1500
        # change company info for csv detai later
        self.env.company.country_id = self.env.ref('base.id')
        self.env.company.account_fiscal_country_id = self.env.company.country_id
        self.env.company.street = "test"
        self.env.company.phone = "12345"

        self.partner_id = self.env['res.partner'].create({"name": "l10ntest", "l10n_id_pkp": True, "l10n_id_kode_transaksi": "01", "l10n_id_nik": "12345", "vat": "000000000000000"})
        self.env['account.tax.group'].create({
            'name': 'tax_group',
            'country_id': self.env.ref('base.id').id,
        })
        self.partner_id_vat = self.env['res.partner'].create({"name": "l10ntest3", "l10n_id_pkp": True, "l10n_id_kode_transaksi": "01", "l10n_id_nik": "67890", "vat": "010000000000000"})
        self.tax_id = self.env['account.tax'].create({"name": "test tax", "type_tax_use": "sale", "amount": 10.0, "price_include": True})

        self.efaktur = self.env['l10n_id_efaktur.efaktur.range'].create({'min': '0000000000001', 'max': '0000000000010'})
        self.out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 110.0, 'tax_ids': self.tax_id.ids}),
            ],
            'l10n_id_kode_transaksi': "01",
        })
        self.out_invoice_1.action_post()

        self.out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 110.11, 'quantity': 400, 'tax_ids': self.tax_id.ids})
            ],
            'l10n_id_kode_transaksi': '01'
        })
        self.out_invoice_2.action_post()

    def test_efaktur_csv_output_1(self):
        """
        Test to ensure that the output csv data contains tax-excluded prices regardless of whether the tax configuration is tax-included or tax-excluded.
        Current test is using price of 110 which is tax-included with tax of amount 10%. So the unit price listed has to be 100 whereas the original result would have 110 instead.
        """
        # to check the diff when test fails

        efaktur_csv_output = self.out_invoice_1._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        # remaining lines
        line_4 = '"FK","01","0","0000000000001","5","2019","1/5/2019","000000000000000","12345#NIK#NAMA#l10ntest","","100","10","0","","0","0","0","0","INV/2019/00001","0"\n'
        line_5 = '"OF","","","100.00","1.0","100.00","0","100.00","10.00","0","0"\n'

        efaktur_csv_expected = output_head + line_4 + line_5

        self.assertEqual(efaktur_csv_expected, efaktur_csv_output)

    def test_efaktur_csv_output_decimal_place(self):
        """
        Test to ensure that decimal place conversion is only done when inputting to csv
        This is to test original calculation of invoice_line_total_price: invoice_line_total_price = invoice_line_unit_price * line.quantity
        as invoice_line_unit_price is already converted to be tax-excluded and set to the decimal place as configured on the currency, the calculation of total could be flawed.

        In this test case, the tax-included price unit is 110.11, hence tax-excluded is 100.1,
        invoice_line_unit_price will be 100, if we continue with the calculation of total price, it will be 100*400 = 40000
        eventhough the total is supposed to be 100.1*400 = 40040, there is a 40 discrepancy
        """
        efaktur_csv_output = self.out_invoice_2._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        line_4 = '"FK","01","0","0000000000002","5","2019","1/5/2019","000000000000000","12345#NIK#NAMA#l10ntest","","40040","4004","0","","0","0","0","0","INV/2019/00002","0"\n'
        line_5 = '"OF","","","100.10","400.0","40040.00","0","40040.00","4004.00","0","0"\n'

        efaktur_csv_expected = output_head + line_4 + line_5
        self.assertEqual(efaktur_csv_expected, efaktur_csv_output)

    def test_efaktur_use_vat(self):
        """ Test to ensure that the e-faktur uses the VAT on NPWP column of efaktur when
        VAT is non-zeros """
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id_vat.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 110.11, 'quantity': 400, 'tax_ids': self.tax_id.ids})
            ],
            'l10n_id_kode_transaksi': '01'
        })
        out_invoice.action_post()
        efaktur_csv_output = out_invoice._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        line_4 = '"FK","01","0","0000000000003","5","2019","1/5/2019","010000000000000","l10ntest3","","40040","4004","0","","0","0","0","0","INV/2019/00003","0"\n'
        line_5 = '"OF","","","100.10","400.0","40040.00","0","40040.00","4004.00","0","0"\n'

        efaktur_csv_expected = output_head + line_4 + line_5
        self.assertEqual(efaktur_csv_expected, efaktur_csv_output)

    def test_efaktur_no_vat_nik(self):
        """ Test to ensure that when no VAT and NIK is supplied, a RedirectWarning should be raised """
        partner_no_vat_nik = self.env['res.partner'].create({"name": "l10ntest4", "l10n_id_pkp": True, "l10n_id_kode_transaksi": "01"})
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_no_vat_nik.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 110.11, 'quantity': 400, 'tax_ids': self.tax_id.ids})
            ],
            'l10n_id_kode_transaksi': '01'
        })
        out_invoice.action_post()
        with self.assertRaises(RedirectWarning):
            out_invoice._generate_efaktur_invoice(',')

    def test_efaktur_nik_with_no_vat(self):
        """ Test to ensure if there is contact has no VAT but has NIK

        NPWP would contain NIK, NAMA contains customer's name, REFERENSI would contain invoice name with customer's NIK"""

        partner_nik_no_vat = self.env['res.partner'].create({"name": "l10ntest4", "l10n_id_pkp": True, "l10n_id_kode_transaksi": "01", "l10n_id_nik": "1532167"})
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': partner_nik_no_vat.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                (0, 0, {'name': 'line1', 'price_unit': 110.11, 'quantity': 400, 'tax_ids': self.tax_id.ids})
            ],
            'l10n_id_kode_transaksi': '01'
        })
        out_invoice.action_post()

        efaktur_csv_output = out_invoice._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        line_4 = '"FK","01","0","0000000000003","5","2019","1/5/2019","1532167","l10ntest4","","40040","4004","0","","0","0","0","0","INV/2019/00003 1532167","0"\n'
        line_5 = '"OF","","","100.10","400.0","40040.00","0","40040.00","4004.00","0","0"\n'

        efaktur_csv_expected = output_head + line_4 + line_5
        self.assertEqual(efaktur_csv_expected, efaktur_csv_output)

    def test_efaktur_total_rounding_accuracy(self):
        """ Use case:
        Using a tax of 11% price included on every line:

        line | qty | price | subtotal
        1    | 24  | 57851 | 1250832.43
        2    | 24  | 65184 | 1409383.78
        3    | 24  | 77134 | 1667762.16
        4    | 24  | 87835 | 1899135.14
        5    | 20  | 180342| 3249405.41

        Untaxed Amount: 9474250.92
        Taxes: 1042176.08
        Total: 10518936.00

        Efaktur will display both:
        -The detail of the lines.
        and
        - the amount_untaxed and amount_tax rounded to 0 decimals.

        The sum of the lines MUST exactly match with the amount_untaxed and amount_tax.
        Which most of the case won't be happening because sum(rounded(vals)) is usually not equal to rounded(sum(vals))
        when using integers.

        To remediate to that issue we are putting the difference in the amount of the first line.
        """
        # Prepare the test invoice.
        tax_id = self.env["account.tax"].create(
            {"name": "test tax 11", "type_tax_use": "sale", "amount": 11.0, "price_include": True}
        )
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                Command.create({'name': 'line1', 'price_unit': 57851, 'quantity': 24, 'tax_ids': tax_id.ids}),
                Command.create({'name': 'line2', 'price_unit': 65184, 'quantity': 24, 'tax_ids': tax_id.ids}),
                Command.create({'name': 'line3', 'price_unit': 77134, 'quantity': 24, 'tax_ids': tax_id.ids}),
                Command.create({'name': 'line4', 'price_unit': 87835, 'quantity': 24, 'tax_ids': tax_id.ids}),
                Command.create({'name': 'line5', 'price_unit': 180342, 'quantity': 20, 'tax_ids': tax_id.ids}),
            ],
            'l10n_id_kode_transaksi': '01',
        })
        invoice.action_post()
        # Generate the generate efaktur csv.
        efaktur_csv_output = invoice._generate_efaktur_invoice(',')
        # Validate the result: the sum of the lines must exactly match with the amount_untaxed and amount_tax.
        dict_reader = csv.DictReader(efaktur_csv_output.splitlines(), delimiter=",")

        amount_untaxed_total = 0
        amount_tax_total = 0
        amount_untaxed_sum = 0
        amount_tax_sum = 0
        for row in dict_reader:
            row_code = row["FK"]
            # Besides the first row, FK is used for the total row.
            if row_code == "FK":
                amount_untaxed_total = int(row["JUMLAH_DPP"])  # These are rounded to 0 decimal in the file.
                amount_tax_total = int(row["JUMLAH_PPN"])  # These are rounded to 0 decimal in the file.
            # OF lines are the data lines, but also used in another case (for codes). Data lines do not have a KD_JENIS_TRANSAKSI though.
            elif row_code == "OF" and not row["KD_JENIS_TRANSAKSI"]:
                amount_untaxed_sum += float(row["NPWP"])  # These are not.
                amount_tax_sum += float(row["NAMA"])  # These are not.

        self.assertEqual(amount_untaxed_total, amount_untaxed_sum)
        self.assertEqual(amount_tax_total, amount_tax_sum)

    def test_efaktur_do_not_consume_code(self):
        """ Ensure that an invoice with no taxes at all will not consume a code. """
        available_code = self.efaktur.available
        # 1. No taxes
        out_invoice_no_taxes = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": False}),
            ],
            "l10n_id_kode_transaksi": "01",
        })
        out_invoice_no_taxes.action_post()
        # The tax number is not set.
        self.assertFalse(out_invoice_no_taxes.l10n_id_tax_number)
        # No codes have been consumed.
        self.assertEqual(self.efaktur.available, available_code)

        with self.assertRaises(ValidationError, msg='E-faktur is not available for invoices without any taxes.'), self.cr.savepoint():
            out_invoice_no_taxes.download_efaktur()

    def test_efaktur_consume_code(self):
        """ Ensure that an invoice with taxes will consume a code. """
        available_code = self.efaktur.available
        out_invoice_no_taxes = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })
        out_invoice_no_taxes.action_post()
        # The tax number is set.
        self.assertEqual(out_invoice_no_taxes.l10n_id_tax_number, '0100000000000003')
        # A code has been consumed.
        self.assertEqual(self.efaktur.available, available_code - 1)
        # No error is raised when downloading.
        out_invoice_no_taxes.download_efaktur()

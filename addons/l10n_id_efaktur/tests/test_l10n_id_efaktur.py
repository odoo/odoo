import csv

from odoo import Command
from odoo.exceptions import UserError, ValidationError, RedirectWarning
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.l10n_id_efaktur.models.account_move import AccountMove
from odoo.addons.l10n_id_efaktur.models.efaktur_document import FK_HEAD_LIST, LT_HEAD_LIST, OF_HEAD_LIST, _csv_row
from odoo.exceptions import RedirectWarning
from unittest.mock import patch

@tagged('post_install', '-at_install', 'post_install_l10n')
class TestIndonesianEfaktur(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country('id')
    def setUpClass(cls):
        super().setUpClass()

        cls.company.write({
            'street': 'test',
            'phone': '12345',
        })
        cls.partner_id = cls.env['res.partner'].create({"name": "l10ntest", "l10n_id_pkp": True, "l10n_id_kode_transaksi": "01", "l10n_id_nik": "12345", "vat": "000000000000000"})
        cls.partner_id_vat = cls.env['res.partner'].create({"name": "l10ntest3", "l10n_id_pkp": True, "l10n_id_kode_transaksi": "01", "l10n_id_nik": "67890", "vat": "010000000000000"})
        cls.tax_id = cls.env['account.tax'].create({"name": "test tax", "type_tax_use": "sale", "amount": 10.0, "price_include_override": "tax_included"})

        cls.efaktur = cls.env['l10n_id_efaktur.efaktur.range'].create({'min': '0000000000001', 'max': '0000000000010'})
        cls.maxDiff = None

        # multi-company setup
        cls.company_data_2 = cls.setup_other_company()

        # For the sake of unit test of this module, we want to retain the the compute method for field
        # l10n_id_need_kode_transaksi of this module. In the coretax module, l10n_id_need_kode_transaksi
        # is always set to False to prevent the flows of old module to be triggered
        patch_kode_transaksi = patch('odoo.addons.l10n_id_efaktur_coretax.models.account_move.AccountMove._compute_need_kode_transaksi',
                                AccountMove._compute_need_kode_transaksi)
        cls.startClassPatcher(patch_kode_transaksi)
        patch_download_efaktur = patch("odoo.addons.l10n_id_efaktur_coretax.models.account_move.AccountMove.download_efaktur",
                                AccountMove.download_efaktur)
        cls.startClassPatcher(patch_download_efaktur)

    def test_posting_without_code(self):
        """ Make sure that if an invoice has no code computed but the partner has one, we still allow posting but also set the code. """
        # Create an invoice without code on purpose.
        self.partner_id.l10n_id_kode_transaksi = False
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                Command.create({'name': 'line1', 'price_unit': 110.0, 'tax_ids': self.tax_id.ids}),
            ],
        })
        self.assertFalse(out_invoice.l10n_id_kode_transaksi)
        # Set the code and post the invoice
        self.partner_id.l10n_id_kode_transaksi = '01'
        out_invoice.action_post()
        # Ensure that the code was set during posting...
        self.assertEqual(out_invoice.l10n_id_kode_transaksi, '01')
        # ...and that the number was computed
        self.assertEqual(out_invoice.l10n_id_tax_number, '0100000000000001')

    def test_efaktur_csv_output_1(self):
        """
        Test to ensure that the output csv data contains tax-excluded prices regardless of whether the tax configuration is tax-included or tax-excluded.
        Current test is using price of 110 which is tax-included with tax of amount 10%. So the unit price listed has to be 100 whereas the original result would have 110 instead.
        """
        # to check the diff when test fails
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                Command.create({'name': 'line1', 'price_unit': 110.0, 'tax_ids': self.tax_id.ids}),
            ],
            'l10n_id_kode_transaksi': "01",
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        efaktur_csv_output = out_invoice.l10n_id_efaktur_document._generate_efaktur_invoice(',')
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

    def test_efaktur_csv_output_address(self):
        """ Ensure that the address in the output is correct and does not contain the customer name. """
        self.partner_id.write({
            'state_id': self.env.ref('base.state_id_ba').id,
            'country_id': self.env.ref('base.id').id,
            'street': 'Jalan Legian',
            'zip': '80361',
            'city': 'Bali',
            'is_company': True,  # If true of it a commercial partner is set, the name would be in the address unless said not to add it.
        })

        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                Command.create({'name': 'line1', 'price_unit': 110.0, 'tax_ids': self.tax_id.ids}),
            ],
            'l10n_id_kode_transaksi': "01",
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        efaktur_csv_output = out_invoice.l10n_id_efaktur_document._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        # remaining lines
        line_4 = '"FK","01","0","0000000000001","5","2019","1/5/2019","000000000000000","12345#NIK#NAMA#l10ntest","Jalan Legian Bali BA 80361 Indonesia","100","10","0","","0","0","0","0","INV/2019/00001","0"\n'
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
        out_invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_id.id,
            'invoice_date': '2019-05-01',
            'date': '2019-05-01',
            'invoice_line_ids': [
                Command.create({'name': 'line1', 'price_unit': 110.11, 'quantity': 400, 'tax_ids': self.tax_id.ids})
            ],
            'l10n_id_kode_transaksi': '01'
        })
        out_invoice.action_post()
        out_invoice.download_efaktur()

        efaktur_csv_output = out_invoice.l10n_id_efaktur_document._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        line_4 = '"FK","01","0","0000000000001","5","2019","1/5/2019","000000000000000","12345#NIK#NAMA#l10ntest","","40040","4004","0","","0","0","0","0","INV/2019/00001","0"\n'
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
        out_invoice.download_efaktur()

        efaktur_csv_output = out_invoice.l10n_id_efaktur_document._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        line_4 = '"FK","01","0","0000000000001","5","2019","1/5/2019","010000000000000","l10ntest3","","40040","4004","0","","0","0","0","0","INV/2019/00001","0"\n'
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
            out_invoice.download_efaktur()

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
        out_invoice.download_efaktur()

        efaktur_csv_output = out_invoice.l10n_id_efaktur_document._generate_efaktur_invoice(',')
        output_head = '%s%s%s' % (
            _csv_row(FK_HEAD_LIST, ','),
            _csv_row(LT_HEAD_LIST, ','),
            _csv_row(OF_HEAD_LIST, ','),
        )
        line_4 = '"FK","01","0","0000000000001","5","2019","1/5/2019","1532167","l10ntest4","","40040","4004","0","","0","0","0","0","INV/2019/00001 1532167","0"\n'
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
            {"name": "test tax 11", "type_tax_use": "sale", "amount": 11.0, "price_include_override": "tax_included"}
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
        invoice.download_efaktur()
        # Generate the generate efaktur csv.
        efaktur_csv_output = invoice.l10n_id_efaktur_document._generate_efaktur_invoice(',')
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
        self.assertEqual(out_invoice_no_taxes.l10n_id_tax_number, '0100000000000001')
        # A code has been consumed.
        self.assertEqual(self.efaktur.available, available_code - 1)
        # No error is raised when downloading.
        out_invoice_no_taxes.download_efaktur()

    def test_efaktur_post_multi_invoices(self):
        """ Test to amke sure if we post 2 invoices at once, each of them have their own
        separate eTax number"""

        # Create 2 separate invoices
        out_invoices = self.env['account.move'].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        }, {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 120.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        }])

        # Post them together
        out_invoices.action_post()

        # Should consume the number 1 and 2
        self.assertEqual(out_invoices[0].l10n_id_tax_number, "0100000000000001")
        self.assertEqual(out_invoices[1].l10n_id_tax_number, "0100000000000002")

    def test_available_range_count(self):
        """ Test on the correctness of l10n_id_available_range_count computation given ranges
        across multi-company setup """
        company_2 = self.company_data_2['company']
        tax_id = self.env['account.tax'].create({"name": "test tax", "type_tax_use": "sale", "amount": 10.0, "price_include": True, "company_id": company_2.id})

        # create 3 ranges on the other company where one has no availability
        self.env['l10n_id_efaktur.efaktur.range'].create({'min': "%013d" % 21, 'max': '%013d' % 30, 'company_id': company_2.id})
        self.env['l10n_id_efaktur.efaktur.range'].create({'min': "%013d" % 31, 'max': '%013d' % 40, 'company_id': company_2.id})
        self.env['l10n_id_efaktur.efaktur.range'].create({'min': "%013d" % 41, 'max': '%013d' % 50, 'available': 0, 'company_id': company_2.id})

        # Create separate invoice on each company
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
            "company_id": self.company.id,
        }, {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
            "company_id": company_2.id
        }])

        # only 1 available range for first invoice, and 2 for second inovice
        self.assertEqual(invoices[0].l10n_id_available_range_count, 1)
        self.assertEqual(invoices[1].l10n_id_available_range_count, 2)

    # =======================================
    # E-faktur range management related tests
    # =======================================

    def test_change_min_max(self):
        """ Test the value of available when changing min and max of range and
        some restrictions to changing min and max of a range"""
        self.assertEqual(self.efaktur.available, 10)

        # Suppose range is 1 - 10, and because it's unused, availability is 10
        # if range becomes 4 - 10, then we remove 3 available numbers
        self.efaktur.min = "0000000000004"
        self.assertEqual(self.efaktur.available, 7)

        # Vice-versa if we turn range into 3 - 10, then we add 1 available number
        self.efaktur.min = "0000000000003"
        self.assertEqual(self.efaktur.available, 8)

        # If range turns into 3 - 8 , 2 available numbers are removed
        self.efaktur.max = "0000000000008"
        self.assertEqual(self.efaktur.available, 6)

        # If range turns into 3 - 9, there is extra 1 available number
        self.efaktur.max = "0000000000009"
        self.assertEqual(self.efaktur.available, 7)

        # If we update both together, then resulting availalbe number is
        # combined behaviour of changing min and max
        self.efaktur.write({'min': "0000000000005", "max": "0000000000005"})
        self.assertEqual(self.efaktur.available, 1)

        self.efaktur.write({'min': "0000000000008", "max": "0000000000010"})
        self.assertEqual(self.efaktur.available, 3)

        # Reset the e-Faktur range back to 1-10
        self.efaktur.write({'min': "0000000000001"})

        # Suppose we use the range 4 times, then the next_num = 5 and availability = 6
        for i in range(4):
            self.efaktur.pop_number()

        # Once a range is used, then we can't change the min to any number
        with self.assertRaises(ValidationError):
            self.efaktur.write({'min': '0000000000003'})

        # We cannot change the range's max to any number less than or equal to last used numbers
        with self.assertRaises(ValidationError):
            self.efaktur.write({'max': '0000000000003'})

        # If we change the max value to number above the last used number, default behaviour applies
        self.efaktur.write({'max': '0000000000007'})
        self.assertEqual(self.efaktur.available, 3)

    def test_next_num(self):
        """ Test if next_num computation is correct after altering availability.

        Range: 0000000000001 - 0000000000010
        Base availability = 10
        """
        self.assertEqual(self.efaktur.next_num, 1)

        self.efaktur.available = 5
        self.assertEqual(self.efaktur.next_num, 6)

    def test_efaktur_delete_range(self):
        """ Ensure that user can only delete e-Faktur ranges that are unused """
        # Use the main range and should raise error when being deleted
        self.efaktur.pop_number()

        with self.assertRaises(UserError):
            self.efaktur.unlink()

        # If a range is unused, there should be no problem when deleting it
        new_range = self.env['l10n_id_efaktur.efaktur.range'].create({"min": "%013d" % 11, "max": "%013d" % 20})
        new_range.unlink()

    def test_efaktur_release_last_number(self):
        """ Test that range min/max is unaffected if we're returning the last released number of that range
        i.e. range: 1-10, 1 is used and then released back, range still 1-10 with 10 availability
        """
        out_invoice = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })
        out_invoice.action_post()
        self.assertEqual(self.efaktur.available, 9)

        out_invoice.button_draft()
        out_invoice.button_cancel()
        out_invoice.reset_efaktur()

        self.assertEqual(self.efaktur.available, 10)

        # Generate 8 invoices and reset the last invoice, should only add availability without
        # affecting the range
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(8)])
        invoices.action_post()
        self.assertEqual(invoices[-1].l10n_id_tax_number, '0100000000000008')
        self.assertEqual(self.efaktur.available, 2)

        last_inv = invoices[-1]
        last_inv.button_draft()
        last_inv.button_cancel()
        last_inv.reset_efaktur()

        self.assertEqual(self.efaktur.min, '0000000000001')
        self.assertEqual(self.efaktur.max, '0000000000010')
        self.assertEqual(self.efaktur.available, 3)

    def test_efaktur_release_number_not_last(self):
        """ Ensure when the number returned is not last released number, split the efaktur range into 2 parts
        range: 1-10, used up to 2, then release 1 => split range into [1-1] available 1 & [2-10] available 8
        """
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        }, {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        }])
        invoices[0].action_post()
        invoices[1].action_post()

        invoices[0].button_cancel()
        invoices[0].reset_efaktur()

        self.assertEqual(self.efaktur.min, '0000000000001')
        self.assertEqual(self.efaktur.max, '0000000000001')
        self.assertEqual(self.efaktur.available, 1)

        # To ensure getting the exact next range, in case there's other ranges being created
        other_range = self.env['l10n_id_efaktur.efaktur.range'].search(
            [('id', '!=', self.efaktur.id), ('min', '>', self.efaktur.min)],
            limit=1,
            order='min ASC'
        )

        self.assertEqual(other_range.min, '0000000000002')
        self.assertEqual(other_range.max, '0000000000010')
        self.assertEqual(other_range.available, 8)

    # ==========================================
    # Multiple Range Selection on Invoice
    # ==========================================

    def test_multiple_range_select_on_invoice(self):
        """ Test some behaviours related to having multiple available ranges on invoice """
        out_invoice_1 = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })

        # Create another range, and there should be 2 ranges available
        efaktur_range = self.env['l10n_id_efaktur.efaktur.range'].create({'min': '0000000000011', 'max': '0000000000020'})
        self.assertEqual(out_invoice_1.l10n_id_available_range_count, 2)

        # if no range selected for it, we auto-assign the smallest range
        out_invoice_1.action_post()
        self.assertEqual(out_invoice_1.l10n_id_efaktur_range, self.efaktur)
        self.assertEqual(out_invoice_1.l10n_id_tax_number, '0100000000000001')

        # Invoice selects a specific range
        out_invoice_2 = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
            "l10n_id_efaktur_range": efaktur_range.id
        })
        out_invoice_2.action_post()
        self.assertEqual(out_invoice_2.l10n_id_tax_number, '0100000000000011')

    # ============================================
    # Reversing invoice with e-Faktur number
    # ============================================
    def test_efaktur_reverse_invoice_flow(self):
        """ Testing when invoice is created, then we reverse and make replacement invoice,
        the l10n_id_replace_invoice_id is set, then if we confirm it, will generate the correct eTax
        number that replaces the old invoice's"""

        # Create invoice and generate the e-Faktur number
        out_invoice_1 = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })
        out_invoice_1.action_post()
        out_invoice_1.download_efaktur()
        # eTax number of original invoice should be (l10n_id_kode_transaksi)0(faktur number in 13 digits)
        self.assertEqual(out_invoice_1.l10n_id_tax_number, "0100000000000001")

        # Reverse and create the replacement invoice
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=out_invoice_1.ids).create({
            "reason": "Correcting Price",
            "journal_id": out_invoice_1.journal_id.id,
        })
        reversal = move_reversal.reverse_moves(is_modify=True)
        replacement_invoice = self.env['account.move'].browse(reversal['res_id'])

        # Replacement invoice should immediately have the l10n_id_replace_invoice_id
        self.assertEqual(replacement_invoice.l10n_id_replace_invoice_id, out_invoice_1)

        # Correct the unit price, then confirm to generate eTax number
        replacement_invoice.invoice_line_ids[0].price_unit = 150.0
        replacement_invoice.action_post()

        # Replacement invoice now should have etax number of (l10n_id_kode_transaksi)1(13 digit number)
        # where the 13 digit number is the number being used on the original invoice
        self.assertEqual(replacement_invoice.l10n_id_tax_number, "0110000000000001")

    def test_efaktur_show_error_no_document_invoice(self):
        """ Ensuring that when reversing a move and creating replacement invoice
        with l10n_id_replace_invoice_id filled in, it can't generate new tax number unless
        the original invoice has generated l10n_id_efaktur_document"""

        # Create the invoice, post it but not generating the efaktur document
        out_invoice_1 = self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        })
        out_invoice_1.action_post()

        # Reverse move and create replacement invoice
        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=out_invoice_1.ids).create({
            "reason": "Correcting Price",
            "journal_id": out_invoice_1.journal_id.id,
        })
        reversal = move_reversal.reverse_moves(is_modify=True)
        replacement_invoice = self.env['account.move'].browse(reversal['res_id'])

        # should be empty recordset since no efaktur document generated on the original invoice
        self.assertEqual(replacement_invoice.l10n_id_replace_invoice_id, self.env['account.move'])

    # ============================================
    # Test generating e-Faktur document flow
    # ============================================

    def test_efaktur_download_multi_company(self):
        """ Ensure that generating efaktur document for invoices across multi company is not allowed """
        # Setup company
        company_2 = self.company_data_2['company']
        tax_id = self.env['account.tax'].create({"name": "test tax", "type_tax_use": "sale", "amount": 10.0, "price_include": True, "company_id": company_2.id})
        self.env['l10n_id_efaktur.efaktur.range'].create({'min': "%013d" % 21, 'max': '%013d' % 30, 'company_id': company_2.id})

        # Setup company across 2 companies
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
            "company_id": self.company.id,
        }, {
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
            "company_id": company_2.id
        }])

        invoices.action_post()

        # Should raise error because the 2 invoices are from 2 different companies
        with self.assertRaises(UserError):
            (invoices).download_efaktur()

    def test_efaktur_download_separate(self):
        """ Test that when we download separately on 2 invoices, each will link to different document.
        If we try to download the 2 together, a RedirectWarning should be raised """

        empty_document = self.env['l10n_id_efaktur.document']
        # Create 2 invoices
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(2)])

        invoices.action_post()

        # Download efaktur separately
        invoices[0].download_efaktur()
        invoices[1].download_efaktur()

        # l10n_id_efaktur_document should be filled in both documents AND different from each other
        self.assertNotEqual(invoices[0].l10n_id_efaktur_document, empty_document)
        self.assertNotEqual(invoices[1].l10n_id_efaktur_document, empty_document)
        self.assertNotEqual(invoices[0].l10n_id_efaktur_document, invoices[1].l10n_id_efaktur_document)

        # If we try to download together, a RedirectWarning should be raised
        with self.assertRaises(RedirectWarning):
            invoices.download_efaktur()

    def test_efaktur_download_together(self):
        """ Test that when we download efaktur for 2 invoices together, they will refer to the same document
        If we try to download separately on both invoices, RedirectWarning should be raised. """

        empty_document = self.env['l10n_id_efaktur.document']
        # Create 2 invoices
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(2)])

        invoices.action_post()

        # Download efaktur together
        invoices.download_efaktur()

        # document should be filled in and both invoice should refer to the same document
        self.assertNotEqual(invoices[0].l10n_id_efaktur_document, empty_document)
        self.assertNotEqual(invoices[1].l10n_id_efaktur_document, empty_document)
        self.assertEqual(invoices[0].l10n_id_efaktur_document, invoices[1].l10n_id_efaktur_document)

        # If we try to download separately, RedirectWarning should be raised
        with self.assertRaises(RedirectWarning):
            invoices[0].download_efaktur()
        with self.assertRaises(RedirectWarning):
            invoices[1].download_efaktur()

    def test_efaktur_download_reset_draft(self):
        """ Test that after efaktur document is generated on invoices together. When we reset invoice 1
        to draft, it should unlink invoice 1 from doucment while keeping invoice.2. Message should be logged
        on invoice 1 to notify users. Attachment should be unlinked from the document as well"""

        # Create 2 invoices
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(2)])

        invoices.action_post()

        # Download efaktur together
        invoices.download_efaktur()

        # If we set invoice 1 to draft, invoice 1 should be unlinked from list of inovices
        # of that document but keeps invoice 2
        document = invoices[0].l10n_id_efaktur_document
        invoices[0].button_draft()

        self.assertTrue(invoices[0].id not in document.invoice_ids.ids and invoices[1].id in document.invoice_ids.ids)

        # document should have no attachment
        self.assertEqual(document.attachment_id, self.env['ir.attachment'])

    def test_efaktur_download_mismatch_flow(self):
        """ Test the flow when you generate 3 invoices (inv1, inv2, ine) generate document(1) and
        document(2,3). When we try to download inv(1,2) redirect warning would be raised, and it should
        provide the view of 2 documents concerned. Then, we edit such that document(1) adds invoice 2.
        Afterwards, regenerate both documents. We are expected to be able to download invoice(1,2) without error now,
        while also still using the same efaktur document record as before """

        # Generate 3 invoices
        invoices = self.env["account.move"].create([{
            "move_type": "out_invoice",
            "partner_id": self.partner_id.id,
            "invoice_date": "2019-05-01",
            "date": "2019-05-01",
            "invoice_line_ids": [
                Command.create({"name": "line1", "price_unit": 110.0, "tax_ids": self.tax_id.ids}),
            ],
            "l10n_id_kode_transaksi": "01",
        } for i in range(3)])
        invoices.action_post()

        # Generate document in group (1), and (2, 3)
        invoices[0].download_efaktur()
        invoices[1:].download_efaktur()

        # Suppose now we want to generate for (1, 2, 3) instead, it should trigger a redirect warning
        # that includes information on the efaktur document involved

        with self.assertRaises(RedirectWarning) as error:
            invoices[:2].download_efaktur()

        action = error.exception.args[1]
        document_ids = action['domain'][0][2]

        # Make sure the documents involved are only the between the document of 1, 2, and 3
        self.assertEqual(document_ids, invoices.l10n_id_efaktur_document.ids)

        # Store old document id and attachment for before-after comparison in the end
        old_document = invoices[0].l10n_id_efaktur_document

        # Unlink invoice 3 from 2nd document, link to first document and regenerate both the document attachments
        document_to_edit = self.env['l10n_id_efaktur.document'].browse(document_ids)
        document_to_edit[1].invoice_ids = [Command.unlink(invoices[1].id)]
        document_to_edit[1].action_regenerate()

        document_to_edit[0].invoice_ids = [Command.link(invoices[1].id)]
        document_to_edit[0].action_regenerate()

        # Should allow download of invoice(1,2,3) together where the efaktur document is the same as
        # the old invoice 1's document
        invoices[:2].download_efaktur()
        self.assertEqual(invoices[1].l10n_id_efaktur_document, old_document)

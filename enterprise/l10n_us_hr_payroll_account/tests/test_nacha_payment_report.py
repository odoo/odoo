# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import tagged, freeze_time, TransactionCase


@tagged('post_install_l10n', 'post_install', '-at_install')
@freeze_time("2020-12-01 03:45:00")
class TestNacha(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.default_journal_bank = cls.env['account.journal'].search([
                    ('company_id', '=', cls.env.company.id),
                    ('type', '=', 'bank')
                ], limit=1)
        cls.default_journal_bank.write({
            "nacha_immediate_destination": "111111118",
            "nacha_immediate_origin": "IMM_ORIG",
            "nacha_destination": "DESTINATION",
            "nacha_company_identification": "COMPANY",
            "nacha_origination_dfi_identification": "ORIGINATION_DFI",
        })
        cls.default_journal_bank.bank_account_id = cls.env["res.partner.bank"].create({
            "partner_id": cls.env.company.partner_id.id,
            "acc_number": "223344556",
            "aba_routing": "123456780",
        })

        # Test that we always put times/dates as seen in the user's timezone.
        # 2020-12-01 03:45:00 UTC is 2020-11-30 19:45:00 US/Pacific
        cls.env.user.tz = "America/Los_Angeles"

        def create_employee_with_bank_account(employee_name):
            employee_id = cls.env['hr.employee'].create({
                'name': employee_name
            })
            # Create employee bank account
            bank_account = cls.env["res.partner.bank"].create({
                "partner_id": employee_id.work_contact_id.id,
                "acc_number": "GB94BARC10201530093459",
                "aba_routing": "123456780",
                'allow_out_payment': True,
            })
            employee_id.bank_account_id = bank_account.id
            return employee_id

        def create_contract(contract_name, state, wage, start, employee_id):
            return cls.env['hr.contract'].create({
                'name': contract_name,
                'employee_id': employee_id.id,
                'state': state,
                'wage': wage,
                'date_start': start,
            })

        def create_employees_with_contracts(no_employees):
            employee_ids = cls.env['hr.employee']
            contract_ids = cls.env['hr.contract']
            contract_start_date = fields.Date.start_of(fields.Date.today(), "year")
            for i in range(1, no_employees + 1):
                employee_id = create_employee_with_bank_account('employee_' + str(i))
                contract_id = create_contract('contract_' + str(i), 'open', i * 2000, contract_start_date, employee_id)
                employee_ids |= employee_id
                contract_ids |= contract_id
            return employee_ids, contract_ids

        def create_and_compute_payslip_run(employee_ids):
            payslip_date = fields.Date.today() + relativedelta(day=1)
            payslip_run_id = cls.env['hr.payslip.run'].create({
                'name': 'Payslip Run',
                'date_start': payslip_date
            })
            for employee_id in employee_ids:
                # Create the employee's payslip and link it to the payslip_run_id
                payslip_id = cls.env['hr.payslip'].create({
                    'name': employee_id.name + '_payslip',
                    'employee_id': employee_id.id,
                    'payslip_run_id': payslip_run_id.id,
                    'struct_id': cls.env.ref('hr_payroll.default_structure', False).id,
                    "date_from": payslip_date,
                })
                payslip_id.compute_sheet()
                payslip_id.action_payslip_done()
            return payslip_run_id

        cls.employee_ids, cls.contract_ids = create_employees_with_contracts(no_employees=2)
        cls.payslip_run_id = create_and_compute_payslip_run(cls.employee_ids)

    def convert_payslip_to_payment(self, payslip):
        return self.env['account.payment'].new({
            "partner_id": payslip.employee_id.work_contact_id.id,
            "partner_bank_id": payslip.employee_id.bank_account_id.id,
            "amount": payslip.net_wage,
            "date": fields.Date.today(),
        })

    def generate_batch_entry_detail_records(self):
        entry_detail_records = []
        for payment_nr, payslip in enumerate(self.payslip_run_id.slip_ids):
            payslip_payment = self.convert_payslip_to_payment(payslip)
            entry_detail_records.append(self.generate_batch_entry_detail_record(payment_nr, payslip_payment, False))
        return entry_detail_records

    def generate_batch_entry_detail_record(self, payment_nr, payment, is_offset):
        transaction_code = "27" if is_offset else "22"
        payslip_amount_in_cents = round(payment.amount * 100)
        partner_name = 'OFFSET' if is_offset else payment.partner_id.name
        partner_iban = payment.partner_bank_id.acc_number
        return f"6{transaction_code}123456780{partner_iban:17.17}{payslip_amount_in_cents:010d}               {partner_name:22.22}  0ORIGINAT{payment_nr:07d}"

    def get_payslips_total_amount_cents(self):
        payslip_total_amount_in_cents = 0
        for payslip in self.payslip_run_id.slip_ids:
            payslip_total_amount_in_cents += round(payslip.net_wage * 100)
        return payslip_total_amount_in_cents

    def generate_padding(self, no_nacha_file_lines):
        no_padding_lines = 0
        if no_nacha_file_lines % 10 != 0:
            no_padding_lines = 10 - no_nacha_file_lines % 10
        # Use 9 for padding. Size of any line in NACHA is 94 bytes.
        padding_line = "9" * 94
        return [padding_line for i in range(no_padding_lines)]

    def generate_nacha_file_records(self):
        payment_report_wizard = self.env['hr.payroll.payment.report.wizard'].create({
            'payslip_run_id': self.payslip_run_id.id,
            'payslip_ids': self.payslip_run_id.slip_ids,
            'export_format': 'nacha',
            'journal_id': self.default_journal_bank.id,
        })
        payment_report_wizard.generate_payment_report()
        # The payment report is encoded to base64 and hence should be decoded.
        generated = base64.b64decode(payment_report_wizard.payslip_run_id.payment_report).splitlines()
        # Each line of the payment report is encoded to bytes using UTF-8 encoding and hence has to be decoded
        generated = [generated_line.decode() for generated_line in generated]
        return generated

    def assertFile(self, generated_file, expected, nr_of_payments, nr_of_batches=1):
        self.assertEqual(
            len(expected) % 10,
            0,
            "NACHA files should always be padded to contain a multiple of 10 lines."
        )

        # File header
        # Per batch:
        #   - batch header
        #   - batch control
        # Each payment (including optional offset payments)
        # File control record
        expected_nr_of_records = 1 + nr_of_batches * 2 + nr_of_payments + 1
        actual_nr_of_records = len([line for line in expected if not line.startswith("9999")])
        self.assertEqual(
            expected_nr_of_records,
            actual_nr_of_records,
            "A incorrect number of records was calculated, it should equal the number of lines in the file (excluding padding)."
        )
        self.assertEqual(len(generated_file), len(expected), "The generated NACHA file has an incorrect amount of records.")

        for generated_line, expected_line in zip(generated_file, expected):
            self.assertEqual(generated_line, expected_line, "Generated line in NACHA file does not match expected.")

    def testGenerateNachaFileUnbalanced(self):

        headers = [
            # header
            f"101 111111118  IMM_ORIG2011301945A094101DESTINATION            {self.env.company.name:23.23}{self.payslip_run_id.id:8d}",
            # batch header
            f"5220{self.env.company.name:16.16}Payslip Run         COMPANY   CCDPAYROLL 0 201130201130   1ORIGINAT0000000",
        ]
        entry_detail_records = self.generate_batch_entry_detail_records()
        total_payslips_amount_in_cents = self.get_payslips_total_amount_cents()
        control_records = [
            # batch control record
            f"82200000020024691356000000000000{total_payslips_amount_in_cents:012d}COMPANY                            ORIGINAT0000000",
            # file control record
            f"9000001000001000000020024691356000000000000{total_payslips_amount_in_cents:012d}                                       ",
        ]
        expected = headers + entry_detail_records + control_records
        padding = self.generate_padding(len(expected))
        expected.extend(padding)
        self.assertFile(self.generate_nacha_file_records(), expected, len(self.payslip_run_id.slip_ids))

    def testGenerateNachaFileBalanced(self):
        journal = self.default_journal_bank
        journal.nacha_is_balanced = True
        journal.nacha_discretionary_data = "00000000000123456789"
        headers = [
            # header
            f"101 111111118  IMM_ORIG2011301945A094101DESTINATION            {self.env.company.name:23.23}{self.payslip_run_id.id:8d}",
            # batch header
            f"5200{self.env.company.name:16.16}00000000000123456789COMPANY   CCDPAYROLL 0 201130201130   1ORIGINAT0000000",
        ]
        entry_detail_records = self.generate_batch_entry_detail_records()
        # Add the offset entry detail record to the entry detail records
        offset_payment = self.env["account.payment"].new({
            "partner_id": journal.company_id.partner_id.id,
            "partner_bank_id": journal.bank_account_id.id,
            "amount": sum(payslip.net_wage for payslip in self.payslip_run_id.slip_ids),
            "memo": "OFFSET",
        })
        entry_detail_records.append(self.generate_batch_entry_detail_record(payment_nr=len(self.payslip_run_id.slip_ids),
                                                                            payment=offset_payment,
                                                                            is_offset=True))
        total_payslips_amount_in_cents = self.get_payslips_total_amount_cents()
        control_records = [
            # batch control record
            f"82000000030037037034{total_payslips_amount_in_cents:012d}{total_payslips_amount_in_cents:012d}COMPANY                            ORIGINAT0000000",
            # file control record
            f"9000001000001000000030037037034{total_payslips_amount_in_cents:012d}{total_payslips_amount_in_cents:012d}                                       ",
        ]
        expected = headers + entry_detail_records + control_records
        padding = self.generate_padding(len(expected))
        expected.extend(padding)
        nr_of_offset_records = len([line for line in expected if line.startswith("627")])
        self.assertFile(self.generate_nacha_file_records(), expected, len(self.payslip_run_id.slip_ids) + nr_of_offset_records)

    def testFileIdModifier(self):
        journal = self.default_journal_bank
        employee = self.env['hr.employee'].create({
            'name': 'test emp',
        })
        # Setting nacha_effective_date on the payslip means that a NACHA file has been generated for that payslip
        self.env['hr.payslip'].create({
            'name': 'payslip',
            'employee_id': employee.id,
            'nacha_effective_date': fields.Date.today() + relativedelta(days=-1)
        })
        # Setting nacha_effective_date on the payslip batch means that a NACHA file has been generated for that batch
        self.env['hr.payslip.run'].create({
            'name': 'batch',
            'nacha_effective_date': fields.Date.today() + relativedelta(days=-1)
        })
        # Create an account.batch.payment and set its payment_method to NACHA and its state to sent
        x = self.env['account.batch.payment'].create({
            'journal_id': journal.id,
            'payment_method_id': self.env.ref('l10n_us_payment_nacha.account_payment_method_nacha').id,
            'date': fields.Date.today() + relativedelta(days=-1)
        })
        x.state = 'sent'
        header_record = self.generate_nacha_file_records()[0]
        # The File Id Modifier is the 34th character of the NACHA file header.
        self.assertEqual(header_record[33], 'D', 'The File Id Modifier in the header should be C as the generated file is third file to generate on the same date.')

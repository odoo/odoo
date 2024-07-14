# coding: utf-8
import base64
import math

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def _validate_bank_for_nacha(self, payment):
        bank = payment.partner_bank_id
        if not bank.aba_routing:
            raise ValidationError(_("Please set an ABA routing number on the %s bank account for %s.", bank.display_name, payment.partner_id.display_name))

    def _validate_journal_for_nacha(self):
        journal = self.journal_id
        error_msgs = []

        if not journal.nacha_immediate_destination:
            error_msgs.append(_("Please set a NACHA immediate destination on the %(journal)s journal."))
        if not journal.nacha_immediate_origin:
            error_msgs.append(_("Please set a NACHA immediate origin on the %(journal)s journal."))
        if not journal.nacha_destination:
            error_msgs.append(_("Please set a NACHA destination on the %(journal)s journal."))
        if not journal.nacha_company_identification:
            error_msgs.append(_("Please set a NACHA company identification on the %(journal)s journal."))
        if not journal.nacha_origination_dfi_identification:
            error_msgs.append(_("Please set a NACHA originating DFI identification on the %(journal)s journal."))

        if error_msgs:
            raise ValidationError(
                '\n'.join(error_msgs) % {
                    "journal": journal.display_name,
                }
            )

    def _get_blocking_factor(self):
        # In practice this value is always hardcoded to 10.
        return 10

    def _get_total_cents(self, payments):
        return sum(round(payment.amount * 100) for payment in payments)

    def _generate_nacha_header(self):
        header = []
        header.append("1")  # Record Type Code
        header.append("01")  # Priority Code
        header.append("{:>10.10}".format(self.journal_id.nacha_immediate_destination))  # Immediate Destination
        header.append("{:>10.10}".format(self.journal_id.nacha_immediate_origin))  # Immediate Origin

        now_in_client_tz = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        header.append("{:6.6}".format(now_in_client_tz.strftime("%y%m%d")))  # File Creation Date
        header.append("{:4.4}".format(now_in_client_tz.strftime("%H%M")))  # File Creation Time

        nr = self.search_count([("id", "!=", self.id), ("date", "=", self.date)])
        header.append("{:1.1}".format(chr(min(90, ord("A") + nr))))  # File ID Modifier

        header.append("094")  # Record Size
        header.append("{:02d}".format(self._get_blocking_factor()))  # Blocking Factor
        header.append("1")  # Format Code
        header.append("{:23.23}".format(self.journal_id.nacha_destination))  # Destination
        header.append("{:23.23}".format(self.journal_id.company_id.name))  # Origin or Company Name

        # ideally this would be the display_name but it will be too long
        header.append("{:8d}".format(self.id))  # Reference Code

        return "".join(header)

    def _generate_nacha_batch_header_record(self, date, batch_nr):
        description = f"BATCH {batch_nr}"
        batch = []
        batch.append("5")  # Record Type Code
        batch.append("200" if self.journal_id.nacha_is_balanced else "220")  # Service Class Code
        batch.append("{:16.16}".format(self.journal_id.company_id.name))  # Company Name

        # Truncate beginning of name if needed because that remains more recognizable:
        # "MYBATCH/OUT/2023/00005" becomes "BATCH/OUT/2023/00005" instead of "MYBATCH/OUT/2023/000"
        batch.append("{:>20.20}".format(self.name[-20:]))  # Company Discretionary Data (optional)

        batch.append("{:0>10.10}".format(self.journal_id.nacha_company_identification))  # Company Identification
        batch.append(self.journal_id.nacha_entry_class_code)  # Standard Entry Class Code
        batch.append("{:10.10}".format(description))  # Company Entry Description
        batch.append("{:6.6}".format(date.strftime("%y%m%d")))  # Company Descriptive Date
        batch.append("{:6.6}".format(date.strftime("%y%m%d")))  # Effective Entry Date
        batch.append("{:3.3}".format(""))  # Settlement Date (Julian)
        batch.append("1")  # Originator Status Code
        batch.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Originating DFI Identification
        batch.append("{:07d}".format(batch_nr))  # Batch Number

        return "".join(batch)

    def _generate_nacha_entry_detail(self, payment_nr, payment, is_offset):
        bank = payment.partner_bank_id
        entry = []
        entry.append("6")  # Record Type Code
        entry.append("27" if is_offset else "22")  # Transaction Code
        entry.append("{:8.8}".format(bank.aba_routing[:-1]))  # RDFI Routing Transit Number
        entry.append("{:1.1}".format(bank.aba_routing[-1]))  # Check Digit
        entry.append("{:17.17}".format(bank.acc_number))  # DFI Account Number
        entry.append("{:010d}".format(self._get_total_cents(payment)))  # Amount
        entry.append("{:15.15}".format(payment.partner_id.vat or ""))  # Individual Identification Number (optional)
        entry.append("{:22.22}".format("OFFSET" if is_offset else payment.partner_id.name))  # Individual Name
        entry.append("  ")  # Discretionary Data Field
        entry.append("0")  # Addenda Record Indicator

        # trace number
        entry.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Trace Number (80-87)
        entry.append("{:07d}".format(payment_nr))  # Trace Number (88-94)

        return "".join(entry)

    def _calculate_aba_hash(self, aba_routing):
        # [:-1]: remove check digit
        # [-8:]: lower 8 digits
        return int(aba_routing[:-1][-8:])

    def _calculate_aba_hash_for_payments(self, payments):
        hashes = sum(self._calculate_aba_hash(payment.partner_bank_id.aba_routing) for payment in payments)
        return str(hashes)[-10:]  # take the rightmost 10 characters

    def _generate_nacha_batch_control_record(self, payments, offset_payment, batch_nr):
        control = []
        control.append("8")  # Record Type Code
        control.append("200" if self.journal_id.nacha_is_balanced else "220")  # Service Class Code
        control.append("{:06d}".format(len(payments | offset_payment)))  # Entry/Addenda Count
        control.append("{:0>10}".format(self._calculate_aba_hash_for_payments(payments | offset_payment)))  # Entry Hash
        control.append("{:012d}".format(self._get_total_cents(offset_payment)))  # Total Debit Entry Dollar Amount in Batch
        control.append("{:012d}".format(self._get_total_cents(payments)))  # Total Credit Entry Dollar Amount in Batch
        control.append("{:0>10.10}".format(self.journal_id.nacha_company_identification))  # Company Identification
        control.append("{:19.19}".format(""))  # Message Authentication Code (leave blank)
        control.append("{:6.6}".format(""))  # Reserved (leave blank)
        control.append("{:8.8}".format(self.journal_id.nacha_origination_dfi_identification))  # Originating DFI Identification
        control.append("{:07d}".format(batch_nr))  # Batch Number

        return "".join(control)

    def _get_nr_of_records(self, nr_of_batches, nr_of_payments):
        # File header
        # Per batch:
        #   - batch header
        #   - batch control
        # Each payment (including optional offset payments)
        # File control record
        return 1 + nr_of_batches * 2 + nr_of_payments + 1

    def _generate_nacha_file_control_record(self, nr_of_batches, payments, offset_payments):
        nr_of_payments = len(payments | offset_payments)

        control = []
        control.append("9")  # Record Type Code
        control.append("{:06d}".format(nr_of_batches))  # Batch Count

        # Records / Blocking Factor (always 10).
        # We ceil because we'll pad the file with 999's until a multiple of 10.
        block_count = math.ceil(self._get_nr_of_records(nr_of_batches, nr_of_payments) / self._get_blocking_factor())
        control.append("{:06d}".format(block_count))

        control.append("{:08d}".format(nr_of_payments))  # Entry/ Addenda Count
        control.append("{:0>10}".format(self._calculate_aba_hash_for_payments(payments | offset_payments)))  # Entry Hash

        control.append("{:012d}".format(self._get_total_cents(offset_payments)))  # Total Debit Entry Dollar Amount in File
        control.append("{:012d}".format(self._get_total_cents(payments)))  # Total Credit Entry Dollar Amount in File
        control.append("{:39.39}".format(""))  # Blank

        return "".join(control)

    def _generate_padding(self, nr_of_batches, nr_of_payments):
        padding = []
        nr_of_records = self._get_nr_of_records(nr_of_batches, nr_of_payments)

        while nr_of_records % 10:
            padding.append("9" * 94)
            nr_of_records += 1

        return padding

    def _generate_nacha_file(self):
        journal = self.journal_id
        header = self._generate_nacha_header()
        entries = []
        batch_nr = 0

        offset_payments = self.env["account.payment"]
        for date, payments in sorted(self.payment_ids.grouped("date").items()):
            entries.append(self._generate_nacha_batch_header_record(date, batch_nr))

            for payment_nr, payment in enumerate(payments):
                self._validate_bank_for_nacha(payment)
                entries.append(self._generate_nacha_entry_detail(payment_nr, payment, is_offset=False))

            offset_payment = self.env["account.payment"]
            if journal.nacha_is_balanced:
                if not journal.bank_account_id:
                    raise ValidationError(_("Please set a bank account on the %s journal.", journal.display_name))

                offset_payment = self.env["account.payment"].new({
                    "partner_id": journal.company_id.partner_id.id,
                    "partner_bank_id": journal.bank_account_id.id,
                    "amount": sum(payment.amount for payment in payments),
                    "ref": "OFFSET",
                })
                self._validate_bank_for_nacha(offset_payment)
                offset_payments |= offset_payment
                entries.append(self._generate_nacha_entry_detail(len(payments), offset_payment, is_offset=True))

            entries.append(self._generate_nacha_batch_control_record(payments, offset_payment, batch_nr))
            batch_nr += 1

        entries.append(self._generate_nacha_file_control_record(batch_nr, self.payment_ids, offset_payments))
        entries.extend(self._generate_padding(batch_nr, len(self.payment_ids | offset_payments)))

        return "\r\n".join([header] + entries)

    def _get_methods_generating_files(self):
        res = super(AccountBatchPayment, self)._get_methods_generating_files()
        res.append("nacha")
        return res

    def _generate_export_file(self):
        if self.payment_method_code == "nacha":
            self._validate_journal_for_nacha()
            data = self._generate_nacha_file()
            date = fields.Datetime.today().strftime("%m-%d-%Y")  # US date format
            return {
                "file": base64.encodebytes(data.encode()),
                "filename": "NACHA-%s-%s.txt" % (self.journal_id.code, date),
            }
        else:
            return super(AccountBatchPayment, self)._generate_export_file()

# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64
import math

from odoo import fields, models, _
from odoo.exceptions import ValidationError


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    def _validate_bank_for_nacha(self, payment):
        bank = payment.partner_bank_id
        if not bank.aba_routing:
            raise ValidationError(
                _(
                    "Please set an ABA routing number on the %(account)s bank account for %(partner)s.",
                    account=bank.display_name,
                    partner=payment.partner_id.display_name,
                )
            )

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

    def _get_nr_nacha_files(self):
        return self.search_count([("id", "!=", self.id), ("date", "=", self.date),
                ('payment_method_id', '=', self.env.ref('l10n_us_payment_nacha.account_payment_method_nacha').id),
                ('state', '=', 'sent')])

    def _generate_nacha_header(self):
        now_in_client_tz = fields.Datetime.context_timestamp(self, fields.Datetime.now())
        nr = self._get_nr_nacha_files()

        return "".join((
            "1",  # Record Type Code
            "01",  # Priority Code
            f"{self.journal_id.nacha_immediate_destination:>10.10}",  # Immediate Destination
            f"{self.journal_id.nacha_immediate_origin:>10.10}",  # Immediate Origin
            f"{now_in_client_tz.strftime('%y%m%d'):6.6}",  # File Creation Date
            f"{now_in_client_tz.strftime('%H%M'):4.4}",  # File Creation Time
            f"{chr(min(90, ord('A') + nr)):1.1}",  # File ID Modifier
            "094",  # Record Size
            f"{self._get_blocking_factor():02d}",  # Blocking Factor
            "1",  # Format Code
            f"{self.journal_id.nacha_destination:23.23}",  # Destination
            f"{self.journal_id.company_id.name:23.23}",  # Origin or Company Name
            f"{self.id:8d}",  # Reference Code, ideally this would be the display_name but it will be too long
        ))

    def _generate_nacha_batch_header_record(self, date, batch_nr):
        description = f"BATCH {batch_nr}"
        return "".join((
            "5",  # Record Type Code
            "200" if self.journal_id.nacha_is_balanced else "220",  # Service Class Code
            f"{self.journal_id.company_id.name:16.16}",  # Company Name
            # Truncate beginning of name if needed because that remains more recognizable:
            # "MYBATCH/OUT/2023/00005" becomes "BATCH/OUT/2023/00005" instead of "MYBATCH/OUT/2023/000"
            f"{self.journal_id.nacha_discretionary_data or self.name[-20:]:20.20}",  # Company Discretionary Data (optional)
            f"{self.journal_id.nacha_company_identification:10.10}",  # Company Identification
            self.journal_id.nacha_entry_class_code,  # Standard Entry Class Code
            f"{description:10.10}",  # Company Entry Description
            f"{date.strftime('%y%m%d'):6.6}",  # Company Descriptive Date
            f"{date.strftime('%y%m%d'):6.6}",  # Effective Entry Date
            f"{'':3.3}",  # Settlement Date (Julian)
            "1",  # Originator Status Code
            f"{self.journal_id.nacha_origination_dfi_identification:8.8}",  # Originating DFI Identification
            f"{batch_nr:07d}",  # Batch Number
        ))

    def _generate_nacha_entry_detail(self, payment_nr, payment, is_offset):
        bank = payment.partner_bank_id
        return "".join((
            "6",  # Record Type Code
            "27" if is_offset else "22",  # Transaction Code
            f"{bank.aba_routing[:-1]:8.8}",  # RDFI Routing Transit Number
            f"{bank.aba_routing[-1]:1.1}",  # Check Digit
            f"{bank.acc_number:17.17}",  # DFI Account Number
            f"{self._get_total_cents(payment):010d}",  # Amount
            f"{payment.partner_id.vat or '':15.15}",  # Individual Identification Number (optional)
            f"{'OFFSET' if is_offset else (bank.acc_holder_name or payment.partner_id.name):22.22}",  # Individual Name
            "  ",  # Discretionary Data Field
            "0",  # Addenda Record Indicator
            f"{self.journal_id.nacha_origination_dfi_identification:8.8}",  # Trace Number (80-87)
            f"{payment_nr:07d}",  # Trace Number (88-94)
        ))

    def _calculate_aba_hash(self, aba_routing):
        # [:-1]: remove check digit
        # [-8:]: lower 8 digits
        return int(aba_routing[:-1][-8:])

    def _calculate_aba_hash_for_payments(self, payments):
        hashes = sum(self._calculate_aba_hash(payment.partner_bank_id.aba_routing) for payment in payments)
        return str(hashes)[-10:]  # take the rightmost 10 characters

    def _generate_nacha_batch_control_record(self, payments, offset_payment, batch_nr):
        return "".join((
            "8",  # Record Type Code
            "200" if self.journal_id.nacha_is_balanced else "220",  # Service Class Code
            f"{len(payments | offset_payment):06d}",  # Entry/Addenda Count
            f"{self._calculate_aba_hash_for_payments(payments | offset_payment):0>10}",  # Entry Hash
            f"{self._get_total_cents(offset_payment):012d}",  # Total Debit Entry Dollar Amount in Batch
            f"{self._get_total_cents(payments):012d}",  # Total Credit Entry Dollar Amount in Batch
            f"{self.journal_id.nacha_company_identification:10.10}",  # Company Identification
            f"{'':19.19}",  # Message Authentication Code (leave blank)
            f"{'':6.6}",  # Reserved (leave blank)
            f"{self.journal_id.nacha_origination_dfi_identification:8.8}",  # Originating DFI Identification
            f"{batch_nr:07d}",  # Batch Number
        ))

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
        # Records / Blocking Factor (always 10).
        # We ceil because we'll pad the file with 999's until a multiple of 10.
        block_count = math.ceil(self._get_nr_of_records(nr_of_batches, nr_of_payments) / self._get_blocking_factor())

        return "".join((
            "9",  # Record Type Code
            f"{nr_of_batches:06d}",  # Batch Count
            f"{block_count:06d}",
            f"{nr_of_payments:08d}",  # Entry/ Addenda Count
            f"{self._calculate_aba_hash_for_payments(payments | offset_payments):0>10}",  # Entry Hash
            f"{self._get_total_cents(offset_payments):012d}",  # Total Debit Entry Dollar Amount in File
            f"{self._get_total_cents(payments):012d}",  # Total Credit Entry Dollar Amount in File
            f"{'':39.39}",  # Blank
        ))

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
                    "memo": "OFFSET",
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
        res = super()._get_methods_generating_files()
        res.append("nacha")
        return res

    def _generate_export_file(self):
        if self.payment_method_code == "nacha":
            self._validate_journal_for_nacha()
            data = self._generate_nacha_file()
            date = fields.Datetime.today().strftime("%m-%d-%Y")  # US date format
            return {
                "file": base64.encodebytes(data.encode()),
                "filename": f"NACHA-{self.journal_id.code}-{date}.txt",
            }
        else:
            return super()._generate_export_file()

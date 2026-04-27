# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo import fields, models, _
from odoo.exceptions import ValidationError, RedirectWarning
from odoo.tools import remove_accents


class AccountBatchPayment(models.Model):
    _inherit = "account.batch.payment"

    l10n_ca_cpa005_file_creation_number = fields.Char(
        string="File Creation Number used in Canadian EFT",
        copy=False,
        help="Leave blank to auto-populate with the next number in the sequence. The FCN is a 4-digit sequence from 0001 "
        "to 9999. This will be used by your bank to identify the file. You can set a value here to override the FCN "
        "sequence just for this payment.",
    )

    def _l10n_ca_cpa005_pre_validate(self):
        journal = self.journal_id
        journal_errors = []
        payments_without_tx_code = self.env["account.payment"]

        if not journal.company_id.l10n_ca_cpa005_short_name:
            raise RedirectWarning(
                _("Please set a Canadian EFT short company name on the %s company.", journal.company_id.display_name),
                journal.company_id._get_records_action(),
                _("Go to company"),
            )

        if not journal.l10n_ca_cpa005_originator_id:
            journal_errors.append(_("- Please set an originator ID on the %(journal)s journal."))
        if not journal.l10n_ca_cpa005_destination_data_center:
            journal_errors.append(_("- Please set a destination data center on the %(journal)s journal."))

        if not journal.bank_account_id:
            journal_errors.append(_("- Please set an account number on the %(journal)s journal."))
        elif not journal.bank_account_id.l10n_ca_financial_institution_number:
            raise RedirectWarning(
                _(
                    "Please set a Financial Institution ID Number on the %(account)s bank account of %(partner)s.",
                    account=journal.bank_account_id.display_name,
                    partner=journal.bank_account_id.partner_id.display_name,
                ),
                journal.bank_account_id._get_records_action(),
                _("Go to bank account"),
            )

        if journal_errors:
            raise RedirectWarning(
                _(
                    "Please fix the following issue(s) on the %(journal)s journal:\n%(errors)s",
                    journal=journal.display_name,
                    errors="\n".join(journal_errors) % {"journal": journal.display_name},
                ),
                journal._get_records_action(),
                _("Go to journal"),
            )

        for payment in self.payment_ids:
            if not payment.l10n_ca_cpa005_transaction_code_id:
                payments_without_tx_code |= payment

        if payments_without_tx_code:
            raise RedirectWarning(
                _(
                    "Please set an EFT/CPA transaction code on the following payment(s):\n%s",
                    "\n".join(f"- {payment.display_name}" for payment in payments_without_tx_code),
                ),
                payments_without_tx_code._get_records_action(name=_("Payments missing EFT/CPA transaction codes")),
                _("Go to payments"),
            )

    def _l10n_ca_cpa005_get_currency(self):
        batch_currency = self.payment_ids.mapped("currency_id")

        if len(batch_currency) != 1:
            raise ValidationError(
                _(
                    "A Canadian EFT file can not contain multiple currencies (%s).",
                    ", ".join(batch_currency.mapped("display_name")),
                )
            )

        if batch_currency not in self.env.ref("base.CAD") | self.env.ref("base.USD"):
            raise ValidationError(
                _(
                    "A Canadian EFT file can not contain %s. It can contain either exclusively payments "
                    "in Canadian dollars or exclusively payments in United States dollars.",
                    batch_currency.display_name,
                )
            )

        return batch_currency

    def _l10n_ca_cpa005_get_total_cents(self, payments):
        return sum(round(payment.amount * 100) for payment in payments)

    def _l10n_ca_cpa005_generate_header(self, currency, file_creation_nr):
        return remove_accents(
            "A"  # 01 1 1 "A" Logical Record Type ID
            "000000001"  # 02 2-10 9 "000000001" Logical Record Count
            f"{self.journal_id.l10n_ca_cpa005_originator_id:10.10}"  # 03 11-20 10 Alphanumeric Originator's ID
            f"{file_creation_nr}"  # 04 21-24 4 Numeric File Creation No.
            f"0{self.date.strftime('%y%j')}"  # 05 25-30 6 Numeric Creation Date
            f"{self.journal_id.l10n_ca_cpa005_destination_data_center:0>5.5}"  # 06 31-35 5 Numeric Destination Data Centre
            f"{' ':20}"  # 07 36-55 20 Alphanumeric Reserved Customer-Direct Clearer Communication area
            f"{currency.name:3.3}"  # 08 56-58 3 Alphanumeric Currency Code Identifier
            f"{' ':1406}"  # 09 59-1464 1406 Alphanumeric Filler
        )

    def _l10n_ca_cpa005_outgoing_payment(self, file_creation_nr, payment, logical_record_count):
        journal = self.journal_id

        return remove_accents(
            "C"  # 01 1 1 "C" Logical Record Type ID
            f"{logical_record_count:09d}"  # 02 2-10 9 Numeric Logical Record Count
            f"{journal.l10n_ca_cpa005_originator_id:10.10}{file_creation_nr}"  # 03 11-24 14 Alphanumeric Origination Control Data (originator ID + Numeric File Creation No.)
            f"{payment.l10n_ca_cpa005_transaction_code_id.code:3.3}"  # 04 25-27 3 Numeric Transaction Type
            f"{self._l10n_ca_cpa005_get_total_cents(payment):010d}"  # 05 28-37 10 Numeric Amount
            f"0{payment.date.strftime('%y%j')}"  # 06 38-43 6 Numeric Date Funds to be Available
            f"{payment.partner_bank_id.l10n_ca_financial_institution_number:0>9}"  # 07 44-52 9 Numeric Institutional Identification No.
            f"{payment.partner_bank_id.acc_number:12.12}"  # 08 53-64 12 Alphanumeric Payee Account No.
            f"{0:022d}"  # 09 65-86 22 Numeric Item Trace No. (RBC says to zero-fill)
            f"{0:03d}"  # 10 87-89 3 Numeric Stored Transaction Type (RBC says to zero-fill)
            f"{journal.company_id.l10n_ca_cpa005_short_name:15.15}"  # 11 90-104 15 Alphanumeric Originator's Short Name
            f"{payment.partner_id.name:30.30}"  # 12 105-134 30 Alphanumeric Payee Name
            f"{journal.company_id.name:30.30}"  # 13 135-164 30 Alphanumeric Originator's Long Name
            f"{journal.l10n_ca_cpa005_originator_id:10.10}"  # 14 165-174 10 Alphanumeric Originating Direct Clearer's User's ID
            f"{(payment.payment_reference or ''):19.19}"  # 15 175-193 19 Alphanumeric Originator's Cross Reference No.
            f"{journal.bank_account_id.l10n_ca_financial_institution_number:0>9}"  # 16 194-202 9 Numeric Institutional ID Number for Returns (RBC says to zero-fill)
            f"{journal.bank_account_id.acc_number:12.12}"  # 17 203-214 12 Alphanumeric Account No. for Returns (RBC says to zero-fill)
            f"{' ':15}"  # 18 215-229 15 Alphanumeric Originator's Sundry Information (optional)
            f"{' ':22}"  # 19 230-251 22 Alphanumeric Filler
            f"{' ':2}"  # 20 252-253 2 Alphanumeric Originator-Direct Clearer Settlement code (RBC says to zero-fill)
            f"{0:011d}"  # 21 254-264 11 Numeric Invalid Data Element I.D.
            f"{' ':1200}"  # padding for segments 2-6, in practice only one payment is provided per record
        )

    def _l10n_ca_cpa005_generate_footer(self, file_creation_nr, logical_record_count):
        journal = self.journal_id
        payments = self.payment_ids

        return remove_accents(
            "Z"  # 01 1 1 "Z" Logical Record Type ID
            f"{logical_record_count:09d}"  # 02 2-10 9 Numeric Logical Record Count
            f"{journal.l10n_ca_cpa005_originator_id:10.10}{file_creation_nr}"  # 03 11-24 14 Alphanumeric Origination Control Data (originator ID + Numeric File Creation No.)
            f"{0:014d}"  # 04 25-38 14 Numeric Total Value of Debit Transactions "D" and "J"
            f"{0:08d}"  # 05 39-46 8 Numeric Total Number of Debit Transactions "D" and "J"
            f"{self._l10n_ca_cpa005_get_total_cents(payments):014d}"  # 06 47-60 14 Numeric Total Value of Credit Transactions "C" and "I"
            f"{len(payments):08d}"  # 07 61-68 8 Numeric Total Number of Credit Transactions "C" and "I"
            f"{0:014d}"  # 08 69-82 14 Numeric Total Value of Error Corrections "E"
            f"{0:08d}"  # 09 83-90 8 Numeric Total Number of Error Corrections "E"
            f"{0:014d}"  # 10 91-104 14 Numeric Total Value of Error Corrections "F"
            f"{0:08d}"  # 11 105-112 8 Numeric Total Number of Error Corrections "F"
            f"{' ':1352}"  # 12 113-1464 1352 Alphanumeric Filler
        )

    def _generate_cpa005_file(self):
        records = []

        self._l10n_ca_cpa005_pre_validate()
        currency = self._l10n_ca_cpa005_get_currency()

        file_creation_nr = self.l10n_ca_cpa005_file_creation_number
        if not file_creation_nr:
            file_creation_nr = self.journal_id._l10n_ca_cpa005_next_file_creation_nr()
            self.l10n_ca_cpa005_file_creation_number = file_creation_nr

        records.append(self._l10n_ca_cpa005_generate_header(currency, file_creation_nr))
        for payment in self.payment_ids:
            records.append(self._l10n_ca_cpa005_outgoing_payment(file_creation_nr, payment, len(records) + 1))
        records.append(self._l10n_ca_cpa005_generate_footer(file_creation_nr, len(records) + 1))

        return "\r\n".join(records)

    def _get_methods_generating_files(self):
        res = super()._get_methods_generating_files()
        res.append("cpa005")
        return res

    def _generate_export_file(self):
        if self.payment_method_code == "cpa005":
            data = self._generate_cpa005_file()
            date = fields.Datetime.today().strftime("%Y-%m-%d")  # CA date format
            return {
                "file": base64.encodebytes(data.encode()),
                "filename": "CPA005-%s-%s.txt" % (self.journal_id.code, date),
            }
        else:
            return super()._generate_export_file()

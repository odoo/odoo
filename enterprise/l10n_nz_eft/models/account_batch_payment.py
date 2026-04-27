# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import csv
import io
from datetime import datetime

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_repr, float_round
from odoo.tools.misc import format_date


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    # ------------------
    # Fields declaration
    # ------------------

    l10n_nz_file_format = fields.Selection(
        string='EFT file format',
        selection=[
            ('anz', 'ANZ'),
            ('bnz', 'BNZ'),
            ('asb', 'ASB'),
            ('westpac', 'DeskBank'),
        ],
    )
    l10n_nz_batch_reference = fields.Char(
        string='Payments Reference',
        help='If sent in bulk, this will be used instead of the payments references.'
    )
    l10n_nz_batch_code = fields.Char(
        string='Analysis Code',
        help='If sent in bulk, this will be used instead of the payments code.'
    )
    l10n_nz_batch_particulars = fields.Char(
        string='Payments Particulars',
        help='If sent in bulk, this will be used instead of the payments particulars.'
    )
    l10n_nz_dd_info = fields.Char(
        string='Direct Debit Information',
        help='For BNZ it should be the Direct Debit Authority\n'
             'For ASB it should be the Registration ID assigned by ASB MSL'
    )
    l10n_nz_company_partner_id = fields.Many2one(related='journal_id.company_id.partner_id')
    l10n_nz_dishonour_account_id = fields.Many2one(
        comodel_name='res.partner.bank',
        string="Dishonour Account",
        help="Used by ANZ as a fallback account in case of dishonored payment.",
        tracking=True,
        domain="[('partner_id','=', l10n_nz_company_partner_id)]",
        check_company=True,
        ondelete='restrict',
    )

    # ----------------
    # Business methods
    # ----------------

    def _get_methods_generating_files(self):
        # EXTENDS account_batch_payment
        res = super()._get_methods_generating_files()
        res.extend(['l10n_nz_eft_in', 'l10n_nz_eft_out'])
        return res

    @api.constrains('batch_type', 'journal_id', 'payment_ids', 'payment_method_id')
    def _check_payments_constrains(self):
        # EXTENDS account_batch_payment
        super()._check_payments_constrains()

        # We store the payment listing indicator on the payment method line, in order to allow more flexibility.
        # For example, the user could set multiple payment method (EFT bulk, EFT Individual,...) and use them to control
        # How payments are made. This means that this indicator must be the same for the whole bulk to avoid needing
        # to generate multiple files.
        for record in self.filtered(lambda batch: batch.payment_method_code in {'l10n_nz_eft_in', 'l10n_nz_eft_out'}):
            if record.payment_ids and len(record.payment_ids.payment_method_line_id.mapped('l10n_nz_payment_listing_indicator')) != 1:
                raise UserError(_("All payments batched using the New Zealand EFT format must have the same payment listing indicator."))

    def validate_batch(self):
        """ Verifies the content of a batch and proceeds to its sending if possible.
        If not, opens a wizard listing the errors and/or warnings encountered.
        """
        # EXTENDS account_batch_payment
        self.ensure_one()
        errors = []
        if self.payment_method_code in {'l10n_nz_eft_in', 'l10n_nz_eft_out'}:
            if not self.l10n_nz_file_format:
                errors.append(_("Please specify a file format before validation."))
            # ANZ does not use this field.
            if self.payment_method_code == 'l10n_nz_eft_in' and self.l10n_nz_file_format in {'bnz', 'asb', 'anz'} and not self.l10n_nz_dd_info:
                errors.append(_("Please specify the Direct Debit Information."))
            if self.l10n_nz_file_format == 'anz' and not self.l10n_nz_dishonour_account_id:
                errors.append(_("For ANZ, you need to specify the Dishonour Account."))
            if not self.journal_id.bank_account_id.acc_number:
                errors.append(_("The bank account of journal %(journal_name)s is missing or the account number is missing.",
                                journal_name=self.journal_id.display_name))

        if errors:
            raise UserError('\n'.join(errors))

        return super().validate_batch()

    @api.model
    def _get_data_export_method(self):
        """ Returns a dict which define which method should be used to export which format.
        Additionally, it also defines if we need to export as csv or text for each format.
        """
        return {
            'anz': (self._export_anz_eft_data, 'csv'),
            'bnz': (self._export_bnz_eft_data, 'txt'),
            'asb': (self._export_asb_eft_data, 'csv'),
            'westpac': (self._export_westpac_eft_data, 'csv'),
        }

    def _generate_export_file(self):
        # EXTENDS account_batch_payment
        self.ensure_one()
        if self.payment_method_code not in {'l10n_nz_eft_in', 'l10n_nz_eft_out'}:
            return super()._generate_export_file()

        # Easier than many ifs, and also provides better support for potential extension/customization.
        data_export_function, file_type = self._get_data_export_method().get(self.l10n_nz_file_format, (None, None))

        if not data_export_function:
            raise UserError(_("The selected file format is not supported."))

        # Export the values
        header, transactions, control = data_export_function()

        # Then write them in a csv or an ASCII txt file (csv is preferred unless not supported)
        if file_type == 'csv':
            output = io.StringIO(newline='')  # https://docs.python.org/3/library/csv.html#id4
            writer = csv.writer(output)

            if header:
                writer.writerow(header)

            for transaction in transactions:
                writer.writerow(transaction)

            if control:
                writer.writerow(control)
            file = base64.encodebytes(output.getvalue().encode())
        else:
            # Note: Only used by BNZ. The doc demands \r\n at the end of each record.
            file_bytes = b''

            if header:
                file_bytes += (','.join(header) + '\r\n').encode('ascii')

            for transaction in transactions:
                file_bytes += (','.join(transaction) + '\r\n').encode('ascii')

            if control:
                file_bytes += (','.join(control) + '\r\n').encode('ascii')
            file = base64.encodebytes(file_bytes)

        file_date = fields.Datetime.context_timestamp(self, datetime.now()).strftime("%Y%m%d%H%M")
        return {
            'filename': f"EFT-{self.journal_id.code}-{file_date}.{file_type}",
            'file': file,
        }

    # ----------------
    # Business methods
    # ----------------

    # -- ANZ format - CSV with Control Record -- #

    def _export_anz_eft_data(self):
        """
        Exports the data of the batch payment in the format expected by the ANZ bank.
        The data returned is used to be written in a CSV file.
        :return: CSV-like data for the header row, transactions rows, and control row.
        """
        is_inbound = self.batch_type == 'inbound'
        is_bulk = not self.payment_ids.payment_method_line_id[0].l10n_nz_payment_listing_indicator

        header = [
            '1',  # Record type, 1 for header
            'D' if is_inbound else 'C',  # Batch type
            format_date(self.env, self.date, date_format='YYYYMMdd'),  # Payment Date
            '',  # Payment Time - Unsupported in odoo
            format_date(self.env, fields.Date.context_today(self), date_format='YYYYMMdd'),  # Batch creation date
            self.journal_id.bank_account_id.acc_number.replace('-', '').replace(' ', ''),  # Funds Account
            self._get_string_within_limit(self.l10n_nz_dd_info, 7) if is_inbound else '',  # DD Code
            'S' if is_bulk else 'M',  # Reporting Method
            self.l10n_nz_dishonour_account_id.acc_number.replace('-', '').replace(' ', ''),  # Dishonour Account
            self._get_string_within_limit(self.name, 12),  # Batch name
            self._get_string_within_limit(self.l10n_nz_batch_particulars, 12),  # Originator Particulars
            self._get_string_within_limit(self.l10n_nz_batch_code, 12),  # Originator Analysis Code
            self._get_string_within_limit(self.l10n_nz_batch_reference, 12, from_left=False),  # Originator Reference
            '',  # Spare
            '',  # Spare
            '',  # Spare
        ]

        transactions = []
        for payment in self.payment_ids.sorted(reverse=True):
            payment_parties_info = self._get_payment_parties_info(payment)
            transactions.append([
                '2',  # Record type, 2 for transaction record
                payment_parties_info['other_party']['account_number'],  # Other party's bank account
                '00' if is_inbound else '50',  # Transaction code, 50 is credit, 00 is debit. 52 can be used for payroll.
                self._get_amount_in_cents_string(payment.amount),  # Transaction amount, in cents.
                self._get_string_within_limit(payment_parties_info['other_party']['name'], 32),  # Other party's name
                payment_parties_info['other_party']['particular'],  # Other party's Particulars
                payment_parties_info['other_party']['code'],  # Other party's code
                payment_parties_info['other_party']['ref'],  # Other party's Reference
                # These three fields are only applicable if Reporting Method is M. Can be left empty to use the batch one.
                payment_parties_info['company_party']['particular'],  # Originator's Particulars.
                payment_parties_info['company_party']['code'],  # Originator's Analysis Code
                payment_parties_info['company_party']['ref'],  # Originator's Reference.
                '',  # reserved
                '',  # reserved
                '',  # reserved
            ])

        control = [
            '3',  # Record type, 3 for Control Record
            self._get_amount_in_cents_string(sum(self.payment_ids.mapped('amount'))) if is_inbound else '',  # Total amount, in cents, for debits.
            self._get_amount_in_cents_string(sum(self.payment_ids.mapped('amount'))) if not is_inbound else '',  # Total amount, in cents, for credits.
            str(len(self.payment_ids)),  # Transaction record count
            self._generate_control_hash(),  # Control hash
            '',  # Spare
            '',  # Spare
            '',  # Spare
        ]

        return header, transactions, control

    # -- BNZ format - ASCII TXT file -- #

    def _export_bnz_eft_data(self):
        """
        Exports the data of the batch payment in the format expected by the ANZ bank.
        The data returned is used to be written in a CSV file.

        The Bulk or Individual Listing Indicator here is the exact one from the field, so check the
        description to see the differences.

        :return: CSV-like data for the header row, transactions rows, and control row.
        """
        is_inbound = self.batch_type == 'inbound'

        header = [
            '1',  # Record type, 1 for header
            self.l10n_nz_dd_info if is_inbound else '',  # Direct Debit Authority Number
            '',  # Spare
            '',  # Spare
            self.journal_id.bank_account_id.acc_number.replace('-', '').replace(' ', ''),  # Bank number / Credit card number.
            '6' if is_inbound else '7',  # File type. 6 for direct debit, 7 for direct credit
            format_date(self.env, self.date, date_format='YYMMdd'),  # Due date
            format_date(self.env, fields.Date.context_today(self), date_format='YYMMdd'),  # File creation date. This date cannot be less than today's date.
            # As this value should be the same for the whole batch, we can take any payment method lines.
            self.payment_ids.payment_method_line_id[0].l10n_nz_payment_listing_indicator or '',  # Bulk or Individual Listing Indicator
        ]

        transactions = []
        for payment in self.payment_ids.sorted(reverse=True):
            payment_parties_info = self._get_payment_parties_info(payment)
            transactions.append([
                '2',  # Record type, 2 for transaction record
                payment_parties_info['other_party']['account_number'],  # Other party's bank account
                '00' if is_inbound else '50',  # Transaction code, 50 is credit, 00 is debit. 52 can be used for payroll.
                self._get_amount_in_cents_string(payment.amount),  # Transaction amount, in cents.
                self._get_string_within_limit(payment_parties_info['other_party']['name'], 20),  # Other party's name
                payment_parties_info['other_party']['ref'],  # Other party's reference
                payment_parties_info['other_party']['code'],  # Other party's code
                '',  # Other Party Alpha Reference - Spare
                payment_parties_info['other_party']['particular'],  # Other party's particular
                self._get_string_within_limit(payment_parties_info['company_party']['name'], 20),  # Company's name
                payment_parties_info['company_party']['code'],  # Company's code
                payment_parties_info['company_party']['ref'],  # Company's reference
                payment_parties_info['company_party']['particular'],  # Company's particular
            ])

        control = [
            '3',  # Record type, 3 for Control Record
            self._get_amount_in_cents_string(sum(self.payment_ids.mapped('amount'))),  # Total amount
            str(len(self.payment_ids)),  # Transaction record count
            self._generate_control_hash(),  # Control hash
        ]

        return header, transactions, control

    # -- ASB format -- #

    def _export_asb_eft_data(self):
        is_inbound = self.batch_type == 'inbound'
        header = None

        # We split dd and dc because the format of the transactions are different.
        transactions = []
        if is_inbound:
            header = [
                20,  # Direct debit identifier
                self._get_string_within_limit(self.l10n_nz_dd_info.replace('-', ''), 15),  # Registration ID assigned by ASB MSL, without hyphens.
                format_date(self.env, self.date, date_format='YYYYMMdd'),  # Due date
                '',  # Client short name, optional and not displayed.
                self._generate_control_hash(),  # Check
                float_repr(sum(self.payment_ids.mapped('amount')), precision_digits=2),  # Total amount, including decimals.
                str(len(self.payment_ids)),  # Transaction record count
            ]

            for payment in self.payment_ids.sorted(reverse=True):
                payment_parties_info = self._get_payment_parties_info(payment)
                transactions.append([
                    payment_parties_info['other_party']['account_number'],  # Deduction Account
                    '000',  # Transaction code, 000 is debit
                    float_repr(payment.amount, precision_digits=2),  # Transaction amount
                    self._get_string_within_limit(payment_parties_info['other_party']['name'], 20),  # Payer name
                    '',  # Party num ref. Should be left empty or filled with 0.
                    payment_parties_info['other_party']['code'],  # Payer Code
                    payment_parties_info['other_party']['ref'],  # Payer ref
                    payment_parties_info['other_party']['particular'],  # Payer particular
                    '',  # Other party name, optional and not displayed.
                    payment_parties_info['company_party']['code'],  # Payee Code
                    payment_parties_info['company_party']['ref'],  # Payee reference
                    payment_parties_info['company_party']['particular'],  # Payee Particulars
                ])
        else:
            for payment in self.payment_ids.sorted(reverse=True):
                payment_parties_info = self._get_payment_parties_info(payment)
                transactions.append([
                    self._get_string_within_limit(self.name, 20),  # Payment name, must be the same for all payments in a single batch.
                    format_date(self.env, self.date, date_format='YYYY/MM/dd'),  # Due date. The use of / is recommended
                    payment_parties_info['company_party']['account_number'],  # Deduction Account
                    float_repr(payment.amount, precision_digits=2),  # Transaction amount.
                    payment_parties_info['other_party']['particular'],  # Payee Particulars
                    payment_parties_info['other_party']['code'],  # Payee Code
                    payment_parties_info['other_party']['ref'],  # Payee Reference
                    payment_parties_info['other_party']['account_number'],  # Destination account
                    payment_parties_info['company_party']['particular'],  # Payer Particulars
                    payment_parties_info['company_party']['code'],  # Payer Code
                    payment_parties_info['company_party']['ref'],  # Payer reference
                    self._get_string_within_limit(payment_parties_info['other_party']['name'], 32),  # Payee name
                ])

        return header, transactions, None

    # -- WESTPAC format -- #

    def _export_westpac_eft_data(self):
        company_account_details = self._get_eft_account_details(self.journal_id.bank_account_id)
        is_inbound = self.batch_type == 'inbound'

        header = [
            'A',  # Record type, A for header
            '1',  # Sequence number
            company_account_details[0],  # Originating Bank. Technically should always be 03 (Westpac).
            company_account_details[1],  # Originating Branch
            self._get_string_within_limit(self.journal_id.bank_account_id.acc_holder_name, 30),  # Customer Name
            '',  # Customer Number - unused
            self._get_string_within_limit(self.l10n_nz_batch_reference, 20),  # Description
            format_date(self.env, self.date, date_format='ddMMYY'),  # Batch due date.
            '',  # Spare - unused
        ]

        transactions = []
        for sequence, payment in enumerate(self.payment_ids.sorted(reverse=True), start=2):
            payment_parties_info = self._get_payment_parties_info(payment)
            transactions.append([
                'D',  # Record type, D for transaction record
                str(sequence),  # Other party's bank account
                # Payee/Payer Account
                *self._get_eft_account_details(payment_parties_info['other_party']['account']),  # Bank number, Branch number, Account number, Account suffix
                '00' if is_inbound else '50',  # Transaction code. 00 for Direct Debit, 50 For payments. 52 for payroll.
                'DD' if is_inbound else 'DC',  # MTS Source.
                self._get_amount_in_cents_string(payment.amount),  # Transaction amount, in cents.
                self._get_string_within_limit(payment_parties_info['other_party']['name'], 20),  # Payee/Payer Name
                payment_parties_info['other_party']['particular'],  # Payee/Payer Particulars
                payment_parties_info['other_party']['code'],  # Payee/Payer Analysis Code
                payment_parties_info['other_party']['ref'],  # Payee/Payer Reference
                # Payer/Payee Account
                *company_account_details,  # Bank number, Branch number, Account number, Account suffix
                self._get_string_within_limit(payment_parties_info['company_party']['name'], 20),  # Payer/Payee Name
                '',  # Spare - Unused
            ])

        return header, transactions, None

    # -- Helpers -- #

    @api.model
    def _get_eft_account_details(self, account):
        """ Split the given account into its details (bank code, branch code, account number, suffix)
        Different banks may have a slightly different format, but it should be easy to parse based on the length.

        The 16 digit format is the standard. Banks using only 2 digits for the suffix usually prefix that by a 0
        BB-bbbb-AAAAAAA-0SS but this 0 is usually optional.

        BNZ claims supporting 19 digits accounts, but I couldn't find any information on that format.
        """
        sanitized_number = account.acc_number.replace('-', '').replace(' ', '')

        if len(sanitized_number) == 15:
            return sanitized_number[:2], sanitized_number[2:6], sanitized_number[6:13], sanitized_number[13:15]
        elif len(sanitized_number) == 16:
            return sanitized_number[:2], sanitized_number[2:6], sanitized_number[6:13], sanitized_number[13:16]
        elif len(sanitized_number) == 17:
            return sanitized_number[:2], sanitized_number[2:6], sanitized_number[6:14], sanitized_number[14:17]
        else:
            raise UserError(_(
                'The format of the account "%s" is not recognized.\n'
                'The supported formats are:\n'
                'BBbbbbAAAAAAASS\n'
                'BBbbbbAAAAAAASSS\n'
                'BBbbbbAAAAAAAASSS', account.acc_number
            ))

    @api.model
    def _get_string_within_limit(self, string, max_length, from_left=True):
        """
        This simple helper takes in a string and a max length, and returns the string formatted to fit the maximum length.
        Supports removing the extra characters from the beginning or the end of the string depending on what is required.

        :param string: The string to format.
        :param max_length: The maximum length of the string as allowed by the format.
        :param from_left: if true extra characters are removed from the end, otherwise from the start.
        :return: The formatted string.
        """
        if not string:
            return ''

        string = string.replace(',', '').strip()
        if from_left:
            string = string[:max_length]
        else:
            string = string[-max_length:]
        # And once more at the end to avoid keeping any that could have been added by the previous operation.
        return string.strip()

    def _get_payment_parties_info(self, payment):
        """
        Depending on the context (inbound, outbound, bulk, ...) we need to get the payment information from different
        places. This helper will help with that by returning a dict with the information of both the company and the
        other party.
        """
        self.ensure_one()
        is_inbound = self.batch_type == 'inbound'

        if is_inbound:
            company_particular = payment.l10n_nz_payee_particulars
            other_particular = payment.l10n_nz_payer_particulars
            company_code = payment.l10n_nz_payee_code
            other_code = payment.l10n_nz_payer_code
            other_party_account = payment.l10n_nz_dd_account_id
        else:
            company_particular = payment.l10n_nz_payer_particulars
            other_particular = payment.l10n_nz_payee_particulars
            company_code = payment.l10n_nz_payer_code
            other_code = payment.l10n_nz_payee_code
            other_party_account = payment.partner_bank_id

        # Particulars, codes and refs are always using the standard format, so we can format here right away.
        return {
            'company_party': {
                'name': self.journal_id.bank_account_id.acc_holder_name,
                'particular': self._get_string_within_limit(company_particular, 12),
                'code': self._get_string_within_limit(company_code, 12),
                'ref': self._get_string_within_limit(payment.memo, 12, from_left=False),
                'account': self.journal_id.bank_account_id,
                'account_number': self.journal_id.bank_account_id.acc_number.replace('-', '').replace(' ', ''),
            },
            'other_party': {
                'name': other_party_account.acc_holder_name,
                'particular': self._get_string_within_limit(other_particular, 12),
                'code': self._get_string_within_limit(other_code, 12),
                'ref': self._get_string_within_limit(payment.memo, 12, from_left=False),
                'account': other_party_account,
                'account_number': other_party_account.acc_number.replace('-', '').replace(' ', ''),
            },
        }

    def _generate_control_hash(self):
        """
        Small helper to generate the control hash of a batch, using the MT9 algorithm, based on the payments inside it.

        The hash total is calculated using the branch and account numbers in each transaction
        record. The bank number and account suffix are not used when calculating the hash total. If
        the account number is 8 digits then the left most digit is excluded from the calculations.

        If the hash total is more than 11 characters, exclude the characters on the left.
        """
        self.ensure_one()
        control_hash = 0
        for payment in self.payment_ids.sorted(reverse=True):
            payment_parties_info = self._get_payment_parties_info(payment)
            payment_account_details = self._get_eft_account_details(payment_parties_info['other_party']['account'])
            # Branch code + account number, as int, are summed up for the control
            control_hash += int(payment_account_details[1] + payment_account_details[2][-7:])
        return str(control_hash)[-11:].zfill(11)

    @api.model
    def _get_amount_in_cents_string(self, amount):
        """ Format the given amount to return the same amount in cents, as a string. """
        return str(int(float_round(amount * 100, precision_digits=0)))

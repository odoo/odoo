# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _

from odoo.exceptions import UserError

from odoo.tools.misc import remove_accents

import itertools

import re

PAYMENT_CODE_MAPPINGS = {
    'dd_sub_init': '01',
    'dd_regular': '17',
    'dd_sub_rep': '18',
    'dd_sub_fin': '19',
}

def format_communication(communication):
    """ Returns a formatted version of the communication given in parameter,
        so that it contains only uppercase characters, numeric characters,
        spaces, and the following punctuation characters: '/' '-' '.' '&'
        (these are the Bacs compliance criteria)
    """
    communication = remove_accents(communication)
    formatted_communication = ''
    for char in communication:
        if char.isalnum() or char in ' /-.,&':
            formatted_communication += char.upper()
        elif char == '_':
            formatted_communication += ' '
    return formatted_communication

class AccountJournal(models.Model):
    _inherit = "account.journal"


    def _default_outbound_payment_methods(self):
        res = super()._default_outbound_payment_methods()
        if self._is_payment_method_available('bacs_dc'):
            res |= self.env.ref('account_bacs.payment_method_bacs_dc')
        return res

    def _default_inbound_payment_methods(self):
        res = super()._default_inbound_payment_methods()
        if self._is_payment_method_available('bacs_dd'):
            res |= self.env.ref('account_bacs.payment_method_bacs_dd')
        return res

    def create_bacs_file(self, payments, payment_method_code, serial_number, bacs_multi_mode, processing_date, expiry_date, batch_ref, creation_date):
        """ Create a Bacs file for the given payments, and returns it as a string.
            The file is created according to the Bacs format specification.
        """
        company = self.company_id
        bacs_sun = company.bacs_sun
        bacs_file = ''
        bacs_file += self._create_header(serial_number, bacs_sun, bacs_multi_mode, processing_date, expiry_date, creation_date)
        company_bank = self.bank_account_id

        # format company and batch details
        company_account_number = company_bank.sanitized_acc_number[8:]
        company_name = format_communication(self.company_id.name)[:18].ljust(18)
        ref = format_communication(batch_ref)[:18].ljust(18)
        if re.match(r'^BATCH/(IN|OUT)/\d{4}/\d+$', batch_ref):
            batch_ref_split = batch_ref.split('/', 1)
            if len(batch_ref_split) > 1:
                ref = format_communication(batch_ref_split[1])[:18].ljust(18)

        if payment_method_code == 'bacs_dc':
            payments_details = self._create_dc_payments(payments, bacs_multi_mode, ref, company_name, company_account_number)
        else:
            payments_details = self._create_dd_payments(payments, bacs_multi_mode, ref, company_name, company_account_number)

        bacs_file += payments_details['payments']
        bacs_file += self._create_footer(payments_details, serial_number, bacs_sun, creation_date, expiry_date)
        return bacs_file

    def _create_header(self, serial_number, bacs_sun, bacs_multi_mode, processing_date, expiry_date, creation_date):
        """ Create the header of the Bacs file, according to the Bacs format specification.
        """
        formatted_processing_date = processing_date.strftime(" %y%j")
        formatted_creation_date = creation_date.strftime(" %y%j")
        formatted_expiration_date = expiry_date.strftime(" %y%j")
        uhl_date = ' ' * 6 if bacs_multi_mode else formatted_processing_date
        uhl_work_code = '4 MULTI  ' if bacs_multi_mode else '1 DAILY  '
        sun_or_whitespaces = bacs_sun if bacs_sun != 'HSBC' else ' ' * 6

        header = ''
        header += f"VOL1{serial_number} {' ' * 20}{'HSBC  ' if bacs_sun == 'HSBC' else ' ' * 6}{' ' * 4}{sun_or_whitespaces}{' ' * 4}{' ' * 28}1\n"
        header += f"HDR1A{sun_or_whitespaces}S  1{sun_or_whitespaces}{serial_number}00010001{' ' * 6}{formatted_creation_date}{formatted_expiration_date}{' ' * 27}\n"
        header += f"HDR2F0200000100{' ' * 65}\n"
        header += f"UHL1{uhl_date}{bacs_sun if bacs_sun != 'HSBC' else '999999'}    00{'0' * 6}{uhl_work_code}{' ' * 43}\n"

        return header

    def _create_dc_payments(self, payments, bacs_multi_mode, batch_ref, company_name, company_account_number):
        """ This method generates transaction and contra lines for BACS (Bankers' Automated Clearing Services) Direct Credit payments.
        Parameters:
        - payments (list): A list of dictionaries representing payment data.
        - bacs_multi_mode (bool): If True, the function processes payments in 'multi' mode. If False, it processes payments in 'single' mode.
        - batch_ref (str): The reference of the batch.
        - company_name (str): The name of the company.
        - company_account_number (str): The account number of the company.

        In 'single' mode, the function processes all payments as a single batch.
        In 'multi' mode, it groups payments by date and for each date, it generates transactions and a contra record.

        Each payment dictionary represents a transaction. The method iterates over payments, validates the necessary fields,
        and generates a formatted string line for each payment according to BACS standards.

        After processing all payments of the same date in 'multi' mode (or all payments in 'single' mode),
        it creates a contra record, which is a summary line of the processed transactions.

        Returns:
            dict: A dictionary containing the following keys:
            - 'payments' (str): A string of formatted lines for BACS file, each line represents a transaction or a contra record.
            - 'debit_total' (int): The total amount of debit transactions in pence.
            - 'credit_total' (int): The total amount of credit transactions in pence.
            - 'debit_count' (int): The total number of debit transactions.
            - 'credit_count' (int): The total number of credit transactions.
        """
        debit_total, credit_total = 0, 0
        debit_count, credit_count = 0, 0

        multi_contra_totals = {}
        single_contra_total = 0


        transaction_lines = []
        for payment_date, payments_in_date in itertools.groupby(payments, key=lambda k: k['payment_date']):
            payments_in_date = list(payments_in_date)

            for payment in payments_in_date:
                partner_name = format_communication(payment['partner_name'])[:18].ljust(18)
                partner_bank_iban = payment['partner_bank_iban']
                partner_sort_code = partner_bank_iban[8:14]
                partner_account_number = partner_bank_iban[14:]
                payment_reference = format_communication(payment['ref'])[:18].ljust(18)

                amount = payment['amount']
                amount_in_pence = int(amount * 100)
                transaction_line = f"{partner_sort_code}{partner_account_number}099{company_account_number}    {amount_in_pence:011}{company_name}{payment_reference}{partner_name}"
                credit_total += amount_in_pence
                credit_count += 1
                if bacs_multi_mode:
                    transaction_line += payment_date.strftime(" %y%j") + '\n'
                    multi_contra_totals[payment_date] = multi_contra_totals.get(payment_date, 0) + amount_in_pence
                else:
                    transaction_line += '\n'
                    single_contra_total += amount_in_pence
                transaction_lines.append(transaction_line)
            if bacs_multi_mode:
                contra_total = multi_contra_totals[payment_date]
                if contra_total > 99999999999:
                    raise UserError(_('Contra total for date %s is greater than 999,999,999.99.', payment_date))
                contra = f"{company_account_number}017{company_account_number}    {contra_total:011}{batch_ref}{'CONTRA'.ljust(18)}{company_name}{payment_date.strftime(' %y%j')}\n"

                debit_total += contra_total
                debit_count += 1
                transaction_lines.append(contra)
        if not bacs_multi_mode:
            if single_contra_total > 99999999999:
                raise UserError(_('Contra total for batch is greater than 999,999,999.99.'))
            debit_total += single_contra_total
            debit_count += 1
            contra = f"{company_account_number}017{company_account_number}    {single_contra_total:011}{batch_ref}{'CONTRA'.ljust(18)}{company_name}\n"
            transaction_lines.append(contra)

        return {
            'payments': ''.join(transaction_lines),
            'debit_total': debit_total,
            'credit_total': credit_total,
            'debit_count': debit_count,
            'credit_count': credit_count,
        }

    def _create_dd_payments(self, payments, bacs_multi_mode, batch_ref, company_name, company_account_number):
        """ This method generates transaction and contra lines for BACS (Bankers' Automated Clearing Services) Direct Debit payments.
        Parameters:
        - payments (list): A list of dictionaries representing payment data.
        - bacs_multi_mode (bool): If True, the function processes payments in 'multi' mode. If False, it processes payments in 'single' mode.
        - batch_ref (str): The reference of the batch.
        - company_name (str): The name of the company.
        - company_account_number (str): The account number of the company.

        In 'single' mode, the function processes all payments as a single batch.
        In 'multi' mode, it groups payments by date and for each date, it generates transactions and a contra record.

        Each payment dictionary represents a transaction. The method iterates over payments, validates the necessary fields,
        and generates a formatted string line for each payment according to BACS standards.

        After processing all payments of the same date in 'multi' mode (or all payments in 'single' mode),
        it creates a contra record, which is a summary line of the processed transactions.

        Returns:
            dict: A dictionary containing the following keys:
            - 'payments' (str): A string of formatted lines for BACS file, each line represents a transaction or a contra record.
            - 'debit_total' (int): The total amount of debit transactions in pence.
            - 'credit_total' (int): The total amount of credit transactions in pence.
            - 'debit_count' (int): The total number of debit transactions.
            - 'credit_count' (int): The total number of credit transactions.
        """
        debit_total, credit_total = 0, 0
        debit_count, credit_count = 0, 0

        multi_contra_totals = {}
        single_contra_total = 0

        transaction_lines = []

        # itereate over payments grouped by date
        for payment_date, payments_in_date in itertools.groupby(payments, key=lambda k: k['payment_date']):
            payments_in_date = list(payments_in_date)

            for payment in payments_in_date:
                partner_name = payment['partner_name'][:18].ljust(18)
                ddi = self.env['bacs.ddi'].browse(payment['bacs_ddi_id'])
                if not ddi:
                    raise UserError(_("The payment must be linked to a BACS Direct Debit Instruction in order to generate a Direct Debit File."))
                if ddi.state == 'revoked':
                    raise UserError(_("The BACS Direct Debit Instruction associated to the payment has been revoked and cannot be used anymore."))
                partner_bank_iban = ddi.partner_bank_id.sanitized_acc_number

                partner_sort_code = partner_bank_iban[8:14]
                partner_account_number = partner_bank_iban[14:]
                partner_name = format_communication(partner_name)[:18].ljust(18)

                payment_reference = format_communication(payment['ref'])[:18].ljust(18)

                amount = payment['amount']
                amount_in_pence = int(amount * 100)
                transaction_code = PAYMENT_CODE_MAPPINGS[payment['bacs_payment_type']]
                transaction_line = f"{partner_sort_code}{partner_account_number}0{transaction_code}{company_account_number}    {amount_in_pence:011}{company_name}{payment_reference}{partner_name}"

                debit_total += amount_in_pence
                debit_count += 1

                if bacs_multi_mode:
                    transaction_line += payment_date.strftime(" %y%j") + '\n'
                    multi_contra_totals[payment_date] = multi_contra_totals.get(payment_date, 0) + amount_in_pence
                else:
                    transaction_line += '\n'
                    single_contra_total += amount_in_pence
                transaction_lines.append(transaction_line)
            if bacs_multi_mode:
                contra_total = multi_contra_totals[payment_date]
                if contra_total > 99999999999:
                    raise UserError(_('Contra total for date %s is greater than 999,999,999.99.', payment_date))
                contra = f"{company_account_number}099{company_account_number}    {contra_total:011}{batch_ref}{'CONTRA'.ljust(18)}{company_name}{payment_date.strftime(' %y%j')}\n"

                credit_total += contra_total
                credit_count += 1

                transaction_lines.append(contra)
        if not bacs_multi_mode:
            if single_contra_total > 99999999999:
                raise UserError(_('Contra total for batch is greater than 999,999,999.99.'))
            credit_total += single_contra_total
            credit_count += 1
            contra = f"{company_account_number}099{company_account_number}    {single_contra_total:011}{batch_ref}{'CONTRA'.ljust(18)}{company_name}\n"
            transaction_lines.append(contra)

        return {
            'payments': ''.join(transaction_lines),
            'debit_total': debit_total,
            'credit_total': credit_total,
            'debit_count': debit_count,
            'credit_count': credit_count,
        }

    def _create_footer(self, payments_details, serial_number, bacs_sun, creation_date, expiry_date):
        """ Create the footer of the Bacs file, according to the Bacs format specification.
        """
        formatted_creation_date = creation_date.strftime(" %y%j")
        formatted_expiration_date = expiry_date.strftime(" %y%j")
        debit_total = payments_details['debit_total']
        if debit_total > 9999999999999:
            raise UserError(_('Debit total for batch is greater than 99,999,999,999.99.'))
        credit_total = payments_details['credit_total']
        if credit_total > 9999999999999:
            raise UserError(_('Credit total for batch is greater than 99,999,999,999.99.'))
        debit_count = payments_details['debit_count']
        credit_count = payments_details['credit_count']
        sun_or_whitespaces = bacs_sun if bacs_sun != 'HSBC' else ' ' * 6

        footer = ''
        footer += f"EOF1A{sun_or_whitespaces}S  1{sun_or_whitespaces}{serial_number}00010001{' ' * 6}{formatted_creation_date}{formatted_expiration_date}{' ' * 27}\n"
        footer += f"EOF2F0200000100{' ' * 65}\n"
        footer += f"UTL1{debit_total:013}{credit_total:013}{debit_count:07}{credit_count:07}{' ' * 36}\n"
        return footer

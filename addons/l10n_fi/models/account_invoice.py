# coding=utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) Avoin.Systems 2016
import re
from openerp import api, fields, models, _
from openerp.exceptions import UserError
import logging

log = logging.getLogger(__name__)


def number2numeric(number):

    invoice_number = re.sub(r'\D', '', number)

    if invoice_number == '' or invoice_number is False:
        raise UserError(_('Invoice number must contain numeric characters'))

    # Make sure the base number is 3...19 characters long
    if len(invoice_number) < 3:
        log.warning('Invoice number {} is less than 3 characters long, '
                    'padding to 3 characters with prefix 11.'
                    .format(invoice_number))
        invoice_number = ('11' + invoice_number)[-3:]
    elif len(invoice_number) > 19:
        log.warning('Invoice number {} is over 19 characters long, '
                    'truncating to 19 characters'.format(invoice_number))
        invoice_number = invoice_number[:19]

    return invoice_number


def get_finnish_check_digit(base_number):
    # Multiply digits from end to beginning with 7, 3 and 1 and
    # calculate the sum of the products
    total = sum((7, 3, 1)[idx % 3] * int(val) for idx, val in
                enumerate(base_number[::-1]))

    # Subtract the sum from the next decade. 10 = 0
    return str((10 - (total % 10)) % 10)


def get_rf_check_digits(base_number):
    check_base = base_number + 'RF00'
    # 1. Convert all non-digits to digits
    # 2. Calculate the modulo 97
    # 3. Subtract the remainder from 98
    # 4. Add leading zeros if necessary
    return ''.join(
        ['00', str(98 - (int(''.join(
            [x if x.isdigit() else str(ord(x) - 55) for x in
             check_base])) % 97))])[-2:]


def compute_payment_reference_fi(number):
    # Drop all non-numeric characters
    invoice_number = number2numeric(number)

    # Calculate the Finnish check digit
    check_digit = get_finnish_check_digit(invoice_number)

    return invoice_number + check_digit


def compute_payment_reference_rf(number):
    # Drop all non-numeric characters
    invoice_number = number2numeric(number)

    # Calculate the Finnish check digit
    invoice_number += get_finnish_check_digit(invoice_number)

    # Calculate the RF check digits
    rf_check_digits = get_rf_check_digits(invoice_number)

    return 'RF' + rf_check_digits + invoice_number


class AccountInvoiceFinnish(models.Model):
    _inherit = 'account.invoice'

    # noinspection PyMethodMayBeStatic
    def _compute_payment_reference_rf(self, invoice_number):
        return compute_payment_reference_rf(invoice_number)

    # noinspection PyMethodMayBeStatic
    def _compute_payment_reference_fi(self, invoice_number):
        return compute_payment_reference_fi(invoice_number)

    @api.multi
    def _compute_payment_reference(self):
        for invoice in self:
            ref_type = invoice.payment_reference_type
            if invoice.payment_reference or not ref_type or ref_type == 'none':
                continue

            if invoice.number:
                method_name = '_compute_payment_reference_' + ref_type
                if not hasattr(invoice, method_name):
                    raise NotImplementedError(
                        "Payment reference type {} doesn't have"
                        "a compute method".format(ref_type))

                self.payment_reference = \
                    getattr(invoice, method_name)(invoice.number)

    payment_reference = fields.Char(
        'Payment Reference Number',
        copy=False,
    )

    payment_reference_type = fields.Selection(
        related='company_id.payment_reference_type',
    )

    @api.multi
    def invoice_validate(self):
        res = super(AccountInvoiceFinnish, self).invoice_validate()
        # noinspection PyProtectedMember
        self.filtered(lambda i: i.payment_reference_type != 'none' and
                      i.type == 'out_invoice') \
            ._compute_payment_reference()
        return res

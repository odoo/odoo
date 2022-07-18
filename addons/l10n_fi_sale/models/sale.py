# -*- coding: utf-8 -*-
import re
from odoo import api, models, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def write(self, values):
        # We compute the l10n_fi/SaleOrder.reference from itself the same way
        # we compute the l10n_fi/AccountMove.invoice_payment_ref from its name.
        reference = values.get('reference', False)
        if reference:
            values['reference'] = self.compute_payment_reference_finnish(reference)
        return super().write(values)

    @api.model
    def number2numeric(self, number):
        so_number = re.sub(r'\D', '', number)
        if so_number == '' or so_number is False:
            raise UserError(_('Reference must contain numeric characters'))

        # Make sure the base number is 3...19 characters long
        if len(so_number) < 3:
            so_number = ('11' + so_number)[-3:]
        elif len(so_number) > 19:
            so_number = so_number[:19]

        return so_number

    @api.model
    def get_finnish_check_digit(self, base_number):
        # Multiply digits from end to beginning with 7, 3 and 1 and
        # calculate the sum of the products
        total = sum((7, 3, 1)[idx % 3] * int(val) for idx, val in
                    enumerate(base_number[::-1]))
        # Subtract the sum from the next decade. 10 = 0
        return str((10 - (total % 10)) % 10)

    @api.model
    def compute_payment_reference_finnish(self, number):
        # Drop all non-numeric characters
        so_number = self.number2numeric(number)
        # Calculate the Finnish check digit
        check_digit = self.get_finnish_check_digit(so_number)
        return so_number + check_digit

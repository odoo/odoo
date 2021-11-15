# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PrintPreNumberedChecks(models.TransientModel):
    _name = 'print.prenumbered.checks'
    _description = 'Print Pre-numbered Checks'

    next_check_number = fields.Char(
        'Next Check Number',
        required=True,
        pattern=r'^[0-9]+$',
        help="Sequence number of the next printed check. Can only contain numbers",
    )

    def print_checks(self):
        check_number = int(self.next_check_number)
        number_len = len(self.next_check_number or "")
        payments = self.env['account.payment'].browse(self.env.context['payment_ids'])
        payments.filtered(lambda r: r.state == 'draft').action_post()
        payments.filtered(lambda r: r.state == 'posted' and not r.is_move_sent).write({'is_move_sent': True})
        for payment in payments:
            payment.check_number = '%0{}d'.format(number_len) % check_number
            check_number += 1
        return payments.do_print_checks()

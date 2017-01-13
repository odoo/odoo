# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PrintPreNumberedChecks(models.TransientModel):
    _name = 'print.prenumbered.checks'
    _description = 'Print Pre-numbered Checks'

    next_check_number = fields.Integer('Next Check Number', required=True)

    @api.multi
    def print_checks(self):
        check_number = self.next_check_number
        payments = self.env['account.payment'].browse(self.env.context['payment_ids'])
        payments.filtered(lambda r: r.state == 'draft').post()
        payments.filtered(lambda r: r.state != 'sent').write({'state': 'sent'})
        for payment in payments:
            payment.check_number = check_number
            check_number += 1
        return payments.do_print_checks()

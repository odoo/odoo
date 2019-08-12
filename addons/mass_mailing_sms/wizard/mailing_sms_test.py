# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation


class MassSMSTest(models.TransientModel):
    _name = 'mailing.sms.test'
    _description = 'Test SMS Mailing'

    def _default_numbers(self):
        return self.env.user.partner_id.phone_sanitized or ""

    numbers = fields.Char(string='Number', required=True,
                          default=_default_numbers, help='Comma-separated list of phone numbers')
    sanitized_numbers = fields.Char(compute='_compute_sanitized_numbers')
    mailing_id = fields.Many2one('mailing.mailing', string='Mailing', required=True, ondelete='cascade')

    @api.depends('numbers')
    def _compute_sanitized_numbers(self):
        if self.numbers:
            numbers = [number.strip() for number in self.numbers.split(',')]
            sanitize_res = phone_validation.phone_sanitize_numbers_w_record(numbers, self.env.user)
            sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
            invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]
            if invalid_numbers:
                raise exceptions.UserError(_('Following numbers are not correctly encoded: %s') % repr(invalid_numbers))
            self.sanitized_numbers = ','.join(sanitized_numbers)
        else:
            self.sanitized_numbers = False

    def action_send_sms(self):
        self.ensure_one()
        self.env['sms.api']._send_sms_batch([{
            'res_id': 0,
            'number': number,
            'content': self.mailing_id.body_plaintext,
        } for number in self.sanitized_numbers.split(',')])
        return True

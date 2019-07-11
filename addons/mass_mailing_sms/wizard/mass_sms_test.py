# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.addons.phone_validation.tools import phone_validation


class MassSMSTest(models.TransientModel):
    _name = 'mass.sms.test'
    _description = 'Test Mass SMS'

    numbers = fields.Char(string='Number', required=True, help='Comma-separated list of phone numbers')
    sanitized_numbers = fields.Char(compute='_compute_sanitized_numbers')
    mass_mailing_id = fields.Many2one('mail.mass_mailing', string='Mailing', required=True, ondelete='cascade')

    @api.depends('numbers')
    def _compute_sanitized_numbers(self):
        if self.numbers:
            sanitize_res = phone_validation.phone_sanitize_numbers_string_w_record(self.numbers, self.env.user)
            sanitized_numbers = [info['sanitized'] for info in sanitize_res.values() if info['sanitized']]
            invalid_numbers = [number for number, info in sanitize_res.items() if info['code']]
            if invalid_numbers:
                raise exceptions.UserError(_('Following numbers are not correctly encoded: %s') % repr(invalid_numbers))
            self.sanitized_numbers = ','.join(sanitized_numbers)
        else:
            self.sanitized_numbers = False

    @api.multi
    def action_send_sms(self):
        self.ensure_one()
        self.env['sms.api']._send_sms_batch([{
            'res_id': 0,
            'number': number,
            'content': self.mass_mailing_id.body_plaintext,
        } for number in self.sanitized_numbers.split(',')])
        return True

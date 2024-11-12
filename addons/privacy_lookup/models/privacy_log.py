# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PrivacyLog(models.Model):
    _name = 'privacy.log'
    _description = 'Privacy Log'
    _rec_name = 'user_id'

    date = fields.Datetime(default=fields.Datetime.now, required=True)
    anonymized_name = fields.Char(required=True)
    anonymized_email = fields.Char(required=True)
    user_id = fields.Many2one(
        'res.users', string="Handled By", required=True,
        default=lambda self: self.env.user)
    execution_details = fields.Text()
    records_description = fields.Text(string="Found Records")
    additional_note = fields.Text()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['anonymized_name'] = self._anonymize_name(vals['anonymized_name'])
            vals['anonymized_email'] = self._anonymize_email(vals['anonymized_email'])
        return super().create(vals_list)

    def _anonymize_name(self, label):
        if not label:
            return ''
        if '@' in label:
            return self._anonymize_email(label)
        return ' '.join(e[0] + '*' * (len(e) - 1) for e in label.split(' ') if e)

    def _anonymize_email(self, label):
        def _anonymize_user(label):
            return '.'.join(e[0] + '*' * (len(e) - 1) for e in label.split('.') if e)
        def _anonymize_domain(label):
            if label in ['gmail.com', 'hotmail.com', 'yahoo.com']:  # More than half of addresses domains
                return label
            split_domain = label.split('.')
            return '.'.join([e[0] + '*' * (len(e) - 1) for e in split_domain[:-1] if e] + [split_domain[-1]])
        if not label or '@' not in label:
            return UserError(_('This email address is not valid (%s)', label))
        user, domain = label.split('@')
        return '{}@{}'.format(_anonymize_user(user), _anonymize_domain(domain))

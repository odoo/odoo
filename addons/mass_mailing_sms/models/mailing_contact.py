# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailingContact(models.Model):
    _name = 'mailing.contact'
    _inherit = ['mailing.contact', 'mail.thread.phone']

    mobile = fields.Char(string='Mobile')

    @api.model
    def _from_partners_get_match_unique_field_names(self):
        return super()._from_partners_get_match_unique_field_names() + ['phone_sanitized']

    @api.model
    def _from_partners_get_create_vals(self, partner):
        return super()._from_partners_get_create_vals(partner) | {
            'mobile': partner.phone,
        }

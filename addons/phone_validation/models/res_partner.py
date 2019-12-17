# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class Partner(models.Model):
    _name = 'res.partner'
    _inherit = ['res.partner', 'mail.thread.phone']

    @api.onchange('phone', 'country_id', 'company_id')
    def _onchange_phone_validation(self):
        if self.phone:
            self.phone = self.phone_get_sanitized_number(number_fname='phone', force_format='INTERNATIONAL') or self.phone

    @api.onchange('mobile', 'country_id', 'company_id')
    def _onchange_mobile_validation(self):
        if self.mobile:
            self.mobile = self.phone_get_sanitized_number(number_fname='mobile', force_format='INTERNATIONAL') or self.mobile

    def _phone_get_number_fields(self):
        return ['mobile', 'phone']

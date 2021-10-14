# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.purchase.controllers.portal import CustomerPortal
from odoo.exceptions import ValidationError
from odoo.http import request


class L10nUSCustomerPortal(CustomerPortal):
    OPTIONAL_PARTNER_BANK_FIELDS = {**CustomerPortal.OPTIONAL_PARTNER_BANK_FIELDS, "aba_routing": "aba_routing"}

    def _prepare_address_operation_values(self, read=True, partner_id=None, **post):
        values = super()._prepare_address_operation_values(read, partner_id, **post)
        values["us_country_id"] = request.env['res.country'].search([('code', '=', 'US')], limit=1).id
        return values

    def main_address_bank_details_form_validate(self, bank_data, partner_bank_data):
        error, error_message = super().main_address_bank_details_form_validate(bank_data, partner_bank_data)
        partner = request.env.user.partner_id
        partner_bank_dummy = request.env['res.partner.bank'].new({
            'partner_id': partner.id,
            'acc_number': partner_bank_data['acc_number'],
            'aba_routing': partner_bank_data['aba_routing'],
        })
        try:
            partner_bank_dummy._check_aba_routing()
        except ValidationError as e:
            error["aba_routing"] = 'error'
            error_message.append(e)
        return error, error_message

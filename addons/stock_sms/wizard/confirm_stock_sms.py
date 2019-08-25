# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, exceptions

import requests


class ConfirmStockSms(models.TransientModel):
    _name = 'confirm.stock.sms'
    _description = 'Confirm Stock SMS'

    picking_id = fields.Many2one('stock.picking', required=True)
    company_id = fields.Many2one('res.company', string='Company', required=True, related='picking_id.company_id')
    iap_account = fields.Boolean(compute='_compute_iap_account')

    def _compute_iap_account(self):
        self.iap_account = self.env['iap.account'].get('sms', force_create=False)

    def send_sms(self):
        self.ensure_one()
        if not self.company_id.has_received_warning_stock_sms:
            IAP = self.env['iap.account']
            if not IAP.get('sms', force_create=False):
                IAP.get('sms')
                url = IAP.get_credits_url(service_name='sms', trial=True)
                try:
                    req = requests.get(url)
                    req.raise_for_status()
                except (ValueError, requests.exceptions.ConnectionError, requests.exceptions.MissingSchema, requests.exceptions.Timeout, requests.exceptions.HTTPError):
                    raise exceptions.AccessError('The url that this service requested returned an error. Please contact the author of the app. The url it tried to contact was ' + url)

            self.company_id.has_received_warning_stock_sms = True
        return self.picking_id.button_validate()

    def dont_send_sms(self):
        self.ensure_one()
        if not self.company_id.has_received_warning_stock_sms:
            self.company_id.has_received_warning_stock_sms = True
            self.company_id.stock_move_sms_validation = False
        return self.picking_id.button_validate()

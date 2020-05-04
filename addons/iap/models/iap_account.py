# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import uuid

from odoo import api, fields, models, _


class IapAccount(models.Model):
    _name = 'iap.account'
    _rec_name = 'service_name'
    _description = 'IAP Account'

    service_name = fields.Char()
    brand_name = fields.Char(
        'Name', compute='_compute_brand_name', store=False,
        help='Get commercial branding name for a given IAP service.')
    account_token = fields.Char(default=lambda s: uuid.uuid4().hex)
    company_ids = fields.Many2many('res.company')

    def _compute_brand_name(self):
        for account in self:
            account.brand_name = self._get_brand_name_from_service_name(account.service_name)

    def _get_brand_name_from_service_name(self, service_name):
        return _('IAP Service')

    # ------------------------------------------------------------
    # OLD API (BW COMPAT)
    # -----------------------------------------------------------

    @api.model
    def get(self, service_name, force_create=True):
        return self.env['iap.services']._iap_get_account(service_name, force_create=force_create)

    @api.model
    def get_credits_url(self, service_name, base_url='', credit=0, trial=False):
        return self.env['iap.services'].iap_get_service_credits_url(service_name, credit=credit, trial=trial)

    @api.model
    def get_account_url(self):
        return self.env['iap.services'].iap_get_account_backend_url()

    @api.model
    def get_config_account_url(self):
        return self.env['iap.services'].iap_get_account_backend_url()

    @api.model
    def get_credits(self, service_name):
        return self.env['iap.services']._iap_get_service_credits_balance(service_name)

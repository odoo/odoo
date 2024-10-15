# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models
from odoo.addons import account


class ResCompany(account.ResCompany):

    account_edi_proxy_client_ids = fields.One2many('account_edi_proxy_client.user', inverse_name='company_id')

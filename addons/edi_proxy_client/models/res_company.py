# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    edi_proxy_client_ids = fields.One2many('edi_proxy_client.user', inverse_name='company_id')

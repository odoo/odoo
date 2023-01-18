# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_edi_proxy_client_user_ids = fields.One2many('account_edi_proxy_client.user', inverse_name='company_id')

    def _get_proxy_users(self, edi_format_code=None, edi_operating_mode=None):
        return self.account_edi_proxy_client_user_ids.filtered(
            lambda u: (not edi_format_code or edi_format_code == u.edi_format_code)
                  and (not edi_operating_mode or edi_operating_mode == u.edi_operating_mode))

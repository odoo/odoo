# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.http import request


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    def session_info(self):
        result = super().session_info()
        company = request.env.user.company_id
        result['company_name'] = company.name
        result['company_account_fiscal_country_code'] = company.account_fiscal_country_id.code
        return result

# -*- coding: utf-8 -*-

from odoo import fields, models
from odoo.addons import account


class ResConfigSettings(account.ResConfigSettings):

    vat_check_vies = fields.Boolean(related='company_id.vat_check_vies', readonly=False,
        string='Verify VAT Numbers')

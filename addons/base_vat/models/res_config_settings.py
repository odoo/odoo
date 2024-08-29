# -*- coding: utf-8 -*-
from odoo.addons import base

from odoo import fields, models


class ResConfigSettings(models.TransientModel, base.ResConfigSettings):

    vat_check_vies = fields.Boolean(related='company_id.vat_check_vies', readonly=False,
        string='Verify VAT Numbers')

# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCompany(models.Model, base.ResCompany):

    vat_check_vies = fields.Boolean(string='Verify VAT Numbers')

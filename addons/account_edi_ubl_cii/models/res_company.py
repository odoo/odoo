# -*- coding: utf-8 -*-
from odoo.addons import base
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResCompany(models.Model, base.ResCompany):

    invoice_is_ubl_cii = fields.Boolean('Generate Peppol format by default', default=False)

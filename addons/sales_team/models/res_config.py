# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models

# Empty class but required since it's overridden by sale & crm
class SaleConfigSettings(models.TransientModel):

    _name = 'sale.config.settings'
    _inherit = 'res.config.settings'

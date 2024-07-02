# -*- coding: utf-8 -*-
# Part of Odoo. See COPYRIGHT & LICENSE files for full copyright and licensing details.

import random
import time

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    customer_id = fields.Char('Customer ID')

    def _get_moneris_customer_id(self, country):
        customer_id = "".join([country, 'MON-', time.strftime('%y%m%d'), str(random.randrange(1, 99999)).zfill(5)]).strip()
        return customer_id

    @api.model
    def create(self, values):
        res = super(ResPartner, self).create(values)
        res.customer_id = self._get_moneris_customer_id('CAN_')
        return res

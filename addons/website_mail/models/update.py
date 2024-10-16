# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models
from odoo.addons import mail


class Publisher_WarrantyContract(mail.Publisher_WarrantyContract):

    @api.model
    def _get_message(self):
        msg = super()._get_message()
        msg['website'] = True
        return msg

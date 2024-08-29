# -*- coding: utf-8 -*-
from odoo.addons import mail
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PublisherWarrantyContract(models.AbstractModel, mail.PublisherWarrantyContract):
    _name = "publisher_warranty.contract"


    @api.model
    def _get_message(self):
        msg = super(PublisherWarrantyContract, self)._get_message()
        msg['website'] = True
        return msg

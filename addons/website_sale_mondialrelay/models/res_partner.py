# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.addons import delivery_mondialrelay, website_sale


class ResPartner(website_sale.ResPartner, delivery_mondialrelay.ResPartner):

    def _can_be_edited_by_current_customer(self, *args, **kwargs):
        return super()._can_be_edited_by_current_customer(*args, **kwargs) and not self.is_mondialrelay

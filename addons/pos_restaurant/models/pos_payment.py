# -*- coding: utf-8 -*-
from odoo.addons import point_of_sale
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosPayment(models.Model, point_of_sale.PosPayment):

    def _update_payment_line_for_tip(self, tip_amount):
        """Inherit this method to perform reauthorization or capture on electronic payment."""
        self.ensure_one()
        self.write({
            "amount": self.amount + tip_amount,
        })

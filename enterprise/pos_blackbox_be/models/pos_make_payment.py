# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class PosMakePayment(models.TransientModel):
    _inherit = "pos.make.payment"

    def check(self):
        order = self.env["pos.order"].browse(self.env.context.get("active_id"))

        if order.config_id.certified_blackbox_identifier:
            raise UserError(
                _("Adding additional payments to registered orders is not allowed.")
            )

        return super().check()

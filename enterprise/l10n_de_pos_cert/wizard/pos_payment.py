# -*- coding: utf-8 -*-

from odoo import models, _
from odoo.exceptions import UserError


class PosMakePayment(models.TransientModel):
    _inherit = 'pos.make.payment'

    def check(self):
        if not self.config_id or self.config_id.l10n_de_fiskaly_tss_id:
            raise UserError(_("You can only pay an order from the POS Cashier interface"))
        return super().check()

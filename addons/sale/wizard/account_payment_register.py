# -*- coding: utf-8 -*-
from odoo.addons import account

from odoo import models


class AccountPaymentRegister(models.TransientModel, account.AccountPaymentRegister):

    def _create_payment_vals_from_wizard(self, batch_result):
        vals = super()._create_payment_vals_from_wizard(batch_result)
        # Make sure the account move linked to generated payment
        # belongs to the expected sales team
        # team_id field on account.payment comes from the `_inherits` on account.move model
        vals.update({'team_id': self.line_ids.move_id[0].team_id.id})
        return vals

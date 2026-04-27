# -*- coding: utf-8 -*-

from odoo import models, _


class AccountBatchPayment(models.Model):
    _inherit = 'account.batch.payment'

    def action_open_batch_payment(self):
        self.ensure_one()
        return {
            'name': _("Batch Payment"),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'view_id': self.env.ref('account_batch_payment.view_batch_payment_form').id,
            'res_model': self._name,
            'res_id': self.id,
            'context': {
                'create': False,
                'delete': False,
            },
            'target': 'current',
        }

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    adyen_transaction_ids = fields.One2many(related='transaction_ids.adyen_transaction_ids')

    def action_view_payment_transactions(self):
        if any(provider != 'odoo' for provider in self.transaction_ids.mapped('provider')):
            return super().action_view_payment_transactions()

        action = self.env['ir.actions.act_window']._for_xml_id('adyen_platforms.adyen_transaction_action')
        if len(self.adyen_transaction_ids) == 1:
            action['view_mode'] = 'form'
            action['res_id'] = self.adyen_transaction_ids.id
            action['views'] = []
        else:
            action['domain'] = [('id', 'in', self.adyen_transaction_ids.ids)]

        return action

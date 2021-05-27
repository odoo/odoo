from odoo import models, fields, api


class AccountPayment(models.Model):
    _inherit = "account.payment"

    payment_group_id = fields.Many2one('account.payment.group', 'Payment Group', ondelete='cascade', readonly=True)

    @api.onchange('payment_group_id')
    def onchange_payment_group_id(self):
        if self.payment_group_id.payment_difference:
            self.amount = self.payment_group_id.payment_difference

    def button_open_payment_group(self):
        self.ensure_one()
        return self.payment_group_id.get_formview_action()

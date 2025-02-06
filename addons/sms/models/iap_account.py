# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class IapAccount(models.Model):
    _inherit = 'iap.account'

    sender_name = fields.Char(help="This is the name that will be displayed as the sender of the SMS.", readonly=True)

    def action_open_registration_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': _('Register Account'),
            'view_mode': 'form',
            'res_model': 'sms.account.phone',
            'context': {'default_account_id': self.id},
        }

    def action_open_sender_name_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'target': 'new',
            'name': _('Choose your sender name'),
            'view_mode': 'form',
            'res_model': 'sms.account.sender',
            'context': {'default_account_id': self.id},
        }

    def _get_account_info(self, account_id, balance, information):
        res = super()._get_account_info(account_id, balance, information)
        if account_id.service_name == 'sms':
            res['sender_name'] = information.get('sender_name')
        return res

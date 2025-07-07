# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TestDigest(models.TransientModel):
    _name = 'digest.test'
    _description = 'Sample Digest Wizard'

    digest_id = fields.Many2one('digest.digest', string='Digest', required=True, ondelete='cascade')
    user_id = fields.Many2one('res.users', string='Recipient', domain="[('share', '=', False)]")

    def send_mail_test(self):
        self.ensure_one()
        self.digest_id._action_send_to_user(self.user_id, consume_tips=False, force_send=True)

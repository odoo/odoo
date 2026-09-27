# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class TestDigest(models.TransientModel):
    _name = 'digest.test'
    _description = 'Sample Digest Wizard'

    digest_id = fields.Many2one('digest.digest', string='Digest', required=True, ondelete='cascade')
    user_ids = fields.Many2many('res.users', string='Recipients', domain="[('share', '=', False)]",
                                default=lambda self: self.env.user)

    def send_mail_test(self):
        self.ensure_one()

        for user in self.user_ids:
            self.digest_id._action_send_to_user(user, consume_tips=False, force_send=True)

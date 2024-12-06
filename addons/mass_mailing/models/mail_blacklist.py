# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailBlacklist(models.Model):
    """ Model of blacklisted email addresses to stop sending emails."""
    _inherit = 'mail.blacklist'

    opt_out_reason_id = fields.Many2one(
        'mailing.subscription.optout', string='Opt-out Reason',
        ondelete='restrict',
        tracking=10)

    def _track_subtype(self, init_values):
        self.ensure_one()
        if 'opt_out_reason_id' in init_values and self.opt_out_reason_id:
            return self.env.ref('mail.mt_comment')
        return super()._track_subtype(init_values)

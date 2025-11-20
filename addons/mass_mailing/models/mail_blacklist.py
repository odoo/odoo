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

    def _track_subtype(self, *, fields_iter=None, initial_values=None):
        self.ensure_one()
        if 'opt_out_reason_id' in fields_iter and self.opt_out_reason_id:
            return self.env.ref('mail.mt_comment')
        return super()._track_subtype(fields_iter=fields_iter, initial_values=initial_values)

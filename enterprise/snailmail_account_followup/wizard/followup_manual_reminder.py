# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class FollowupManualReminder(models.TransientModel):
    _inherit = 'account_followup.manual_reminder'

    snailmail = fields.Boolean()
    snailmail_cost = fields.Float(string='Stamps', default=1, readonly=True, compute='_compute_snailmail_cost')

    def _get_defaults_from_followup_line(self, followup_line):
        defaults = super()._get_defaults_from_followup_line(followup_line)
        defaults['print'] = followup_line.send_letter
        return defaults

    @api.depends('partner_id')
    def _compute_snailmail_cost(self):
        for record in self:
            # We send the letter to the main address of the company (self) and the followup contacts
            followup_contacts = record.partner_id._get_all_followup_contacts()
            record.snailmail_cost = len(followup_contacts) + 1

    def _get_wizard_options(self):
        # OVERRIDE account_followup/wizard/followup_manual_reminder.py
        options = super()._get_wizard_options()
        options['snailmail'] = self.snailmail
        return options

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, _
from odoo.exceptions import UserError


class AccountFollowupReport(models.AbstractModel):
    _inherit = "account.followup.report"

    @api.model
    def _send_snailmail(self, options):
        """
        Send by post the followup to the customer's followup contacts
        """
        partner = self.env['res.partner'].browse(options.get('partner_id'))
        followup_contacts = partner._get_all_followup_contacts() or partner
        sent_at_least_once = False
        for to_send_partner in followup_contacts:
            letter = self.env['snailmail.letter'].create({
                'state': 'pending',
                'partner_id': to_send_partner.id,
                'model': 'res.partner',
                'res_id': partner.id,
                'user_id': self.env.user.id,
                'report_template': self.env.ref('account_followup.action_report_followup').id,
                'company_id': to_send_partner.company_id.id or self.env.company.id,
            })
            if self.env['snailmail.letter']._is_valid_address(letter):
                letter._snailmail_print()
                sent_at_least_once = True
        if not sent_at_least_once:
            raise UserError(_('You are trying to send a letter by post, but no follow-up contact has any address set'))

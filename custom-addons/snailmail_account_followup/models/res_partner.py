# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def send_followup_snailmail(self, options):
        """
        Send a follow-up report by post to customers in self
        """
        for record in self:
            options['partner_id'] = record.id
            self.env['account.followup.report']._send_snailmail(options)

    def _send_followup(self, options):
        # OVERRIDE account_followup/models/res_partner.py
        super()._send_followup(options)
        followup_line = options.get('followup_line')
        if options.get('snailmail', followup_line.send_letter):
            self.send_followup_snailmail(options)

    def _has_missing_followup_info(self):
        res = super()._has_missing_followup_info()
        followup_contacts = self._get_all_followup_contacts() or self
        if self.followup_line_id.send_letter \
            and not any(self.env['snailmail.letter']._is_valid_address(to_send_partner)
                        for to_send_partner in followup_contacts):
            return True
        return res

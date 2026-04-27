# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    def _send_sms(self):
        for ticket in self:
            if ticket.partner_id and ticket.stage_id and ticket.stage_id.sms_template_id:
                ticket._message_sms_with_template(template=ticket.stage_id.sms_template_id, partner_ids=ticket.partner_id.ids)

    @api.model_create_multi
    def create(self, vals_list):
        tickets = super().create(vals_list)
        tickets._send_sms()
        return tickets

    def write(self, vals):
        res = super().write(vals)
        if 'stage_id' in vals:
            self._send_sms()
        return res

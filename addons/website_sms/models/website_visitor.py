# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _prepare_visitor_send_sms_values(self):
        if self.partner_id.mobile:
            return {
                'res_model': 'res.partner',
                'res_id': self.partner_id.id,
                'partner_ids': [self.partner_id.id],
                'number_field_name': 'mobile',
            }
        return {}

    def action_send_sms(self):
        self.ensure_one()
        visitor_sms_values = self._prepare_visitor_send_sms_values()
        if not visitor_sms_values:
            raise UserError(_("There is no mobile phone number linked to this visitor."))

        context = dict(self.env.context)
        context.update({
            'default_res_model': visitor_sms_values['res_model'],
            'default_res_id': visitor_sms_values['res_id'],
            'default_composition_mode': 'comment',
            'default_number_field_name': visitor_sms_values['number_field_name'],
        })

        return {
            "type": "ir.actions.act_window",
            "res_model": "sms.composer",
            "view_mode": 'form',
            "context": context,
            "name": "Send SMS Text Message",
            "target": "new",
        }

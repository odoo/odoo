# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    def _check_for_sms_composer(self):
        """ Purpose of this method is to actualize visitor model prior to contacting
        him. Used notably for inheritance purpose, when dealing with leads that
        could update the visitor model. """
        return bool(self.partner_id and (self.partner_id.mobile or self.partner_id.phone))

    def _prepare_sms_composer_context(self):
        return {
            'default_res_model': 'res.partner',
            'default_res_id': self.partner_id.id,
            'default_composition_mode': 'comment',
            'default_number_field_name': 'mobile' if self.partner_id.mobile else 'phone',
        }

    def action_send_sms(self):
        self.ensure_one()
        if not self._check_for_sms_composer():
            raise UserError(_("There are no contact and/or no phone or mobile numbers linked to this visitor."))
        visitor_composer_ctx = self._prepare_sms_composer_context()

        compose_ctx = dict(self.env.context)
        compose_ctx.update(**visitor_composer_ctx)
        return {
            "name": _("Send SMS"),
            "type": "ir.actions.act_window",
            "res_model": "sms.composer",
            "view_mode": 'form',
            "context": compose_ctx,
            "target": "new",
        }

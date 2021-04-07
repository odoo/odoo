# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.from odoo import models

from odoo import models


class Coupon(models.Model):
    _inherit = 'coupon.coupon'

    def action_send_sms(self):
        self.ensure_one()
        template = self.env.ref('coupon_sms.sms_template_data_coupon')
        temp_body = template._render_field('body', self.ids)[self.id]
        ctx = dict(
            default_res_model='res.partner',
            default_res_id=self.partner_id.id,
            default_body=temp_body,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sms.composer',
            'view_mode': 'form',
            'composition_mode': 'comment',
            'target': 'new',
            'context': ctx,
        }

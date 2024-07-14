# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, _

class HelpdeskSaleCouponGenerate(models.TransientModel):
    _name = "helpdesk.sale.coupon.generate"
    _description = 'Generate Sales Coupon from Helpdesk'


    def _get_default_program(self):
        return self.env['loyalty.program'].search([('applies_on', '=', 'current'), ('trigger', '=', 'with_code'), ('program_type', '=', 'coupons')], limit=1)

    ticket_id = fields.Many2one('helpdesk.ticket')
    company_id = fields.Many2one(related="ticket_id.company_id")
    program = fields.Many2one('loyalty.program', string="Coupon Program", default=_get_default_program,
        domain=[('applies_on', '=', 'current'), ('trigger', '=', 'with_code')], check_company=True)
    points_granted = fields.Float('Coupon Value', default=1)
    points_name = fields.Char(related='program.portal_point_name')
    valid_until = fields.Date("Valid Until")

    def _get_default_template(self):
        self.ensure_one()
        return self.program.communication_plan_ids.filtered(lambda m: m.trigger == 'create').mail_template_id[:1]

    def action_coupon_generate_send(self):
        self.ensure_one()
        coupon = self.env['loyalty.card'].with_context(action_no_send_mail=True).sudo().create({
            'partner_id': self.ticket_id.partner_id.id,
            'program_id': self.program.id,
            'points': self.points_granted,
            'expiration_date': self.valid_until,
        })
        self.ticket_id.coupon_ids |= coupon
        self.ticket_id.message_post_with_source(
            'helpdesk.ticket_conversion_link',
            render_values={'created_record': coupon, 'message': _('Coupon created')},
            subtype_xmlid='mail.mt_note',
        )
        coupon.message_post_with_source(
            'mail.message_origin_link',
            render_values={'self': coupon, 'origin': self.ticket_id},
            subtype_xmlid='mail.mt_note',
        )
        default_template = self._get_default_template()
        compose_form_id = self.env['ir.model.data']._xmlid_to_res_id('mail.email_compose_message_wizard_form')
        context = {
            'default_model': 'loyalty.card',
            'default_res_ids': coupon.ids,
            'default_template_id': default_template.id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': 'mail.mail_notification_light',
            'force_email': True,
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': context,
        }

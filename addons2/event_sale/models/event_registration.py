# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_is_zero


class EventRegistration(models.Model):
    _inherit = 'event.registration'

    # TDE FIXME: maybe add an onchange on sale_order_id
    sale_order_id = fields.Many2one('sale.order', string='Sales Order', ondelete='cascade', copy=False)
    sale_order_line_id = fields.Many2one('sale.order.line', string='Sales Order Line', ondelete='cascade', copy=False)
    sale_status = fields.Selection(string="Sale Status", selection=[
            ('to_pay', 'Not Sold'),
            ('sold', 'Sold'),
            ('free', 'Free'),
        ], compute="_compute_registration_status", compute_sudo=True, store=True, precompute=True)
    state = fields.Selection(default=None, compute="_compute_registration_status", store=True, readonly=False, precompute=True)
    utm_campaign_id = fields.Many2one(compute='_compute_utm_campaign_id', readonly=False,
        store=True, ondelete="set null")
    utm_source_id = fields.Many2one(compute='_compute_utm_source_id', readonly=False,
        store=True, ondelete="set null")
    utm_medium_id = fields.Many2one(compute='_compute_utm_medium_id', readonly=False,
        store=True, ondelete="set null")

    @api.depends('sale_order_id.state', 'sale_order_id.currency_id', 'sale_order_line_id.price_total')
    def _compute_registration_status(self):
        for so_line, registrations in self.grouped('sale_order_line_id').items():
            cancelled_so_registrations = registrations.filtered(lambda reg: reg.sale_order_id.state == 'cancel')
            cancelled_so_registrations.state = 'cancel'
            cancelled_registrations = cancelled_so_registrations | registrations.filtered(lambda reg: reg.state == 'cancel')
            if not so_line or float_is_zero(so_line.price_total, precision_rounding=so_line.currency_id.rounding):
                registrations.sale_status = 'free'
                registrations.filtered(lambda reg: not reg.state or reg.state == 'draft').state = "open"
            else:
                sold_registrations = registrations.filtered(lambda reg: reg.sale_order_id.state == 'sale') - cancelled_registrations
                sold_registrations.sale_status = 'sold'
                (registrations - sold_registrations).sale_status = 'to_pay'
                sold_registrations.filtered(lambda reg: not reg.state or reg.state in {'draft', 'cancel'}).state = "open"
                (registrations - sold_registrations - cancelled_registrations).state = 'draft'

    @api.depends('sale_order_id')
    def _compute_utm_campaign_id(self):
        for registration in self:
            if registration.sale_order_id.campaign_id:
                registration.utm_campaign_id = registration.sale_order_id.campaign_id
            elif not registration.utm_campaign_id:
                registration.utm_campaign_id = False

    @api.depends('sale_order_id')
    def _compute_utm_source_id(self):
        for registration in self:
            if registration.sale_order_id.source_id:
                registration.utm_source_id = registration.sale_order_id.source_id
            elif not registration.utm_source_id:
                registration.utm_source_id = False

    @api.depends('sale_order_id')
    def _compute_utm_medium_id(self):
        for registration in self:
            if registration.sale_order_id.medium_id:
                registration.utm_medium_id = registration.sale_order_id.medium_id
            elif not registration.utm_medium_id:
                registration.utm_medium_id = False

    def action_view_sale_order(self):
        action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['views'] = [(False, 'form')]
        action['res_id'] = self.sale_order_id.id
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('sale_order_line_id'):
                so_line_vals = self._synchronize_so_line_values(
                    self.env['sale.order.line'].browse(vals['sale_order_line_id'])
                )
                vals.update(so_line_vals)
        registrations = super(EventRegistration, self).create(vals_list)
        for registration in registrations:
            if registration.sale_order_id:
                registration.message_post_with_source(
                    'mail.message_origin_link',
                    render_values={'self': registration, 'origin': registration.sale_order_id},
                    subtype_xmlid='mail.mt_note',
                )
        return registrations

    def write(self, vals):
        if vals.get('sale_order_line_id'):
            so_line_vals = self._synchronize_so_line_values(
                self.env['sale.order.line'].browse(vals['sale_order_line_id'])
            )
            vals.update(so_line_vals)

        if vals.get('event_ticket_id'):
            self.filtered(
                lambda registration: registration.event_ticket_id and registration.event_ticket_id.id != vals['event_ticket_id']
            )._sale_order_ticket_type_change_notify(self.env['event.event.ticket'].browse(vals['event_ticket_id']))

        return super(EventRegistration, self).write(vals)

    def _synchronize_so_line_values(self, so_line):
        if so_line:
            return {
                # Avoid registering public users but respect the portal workflows
                'partner_id': False if self.env.user._is_public() and self.env.user.partner_id == so_line.order_id.partner_id else so_line.order_id.partner_id.id,
                'event_id': so_line.event_id.id,
                'event_ticket_id': so_line.event_ticket_id.id,
                'sale_order_id': so_line.order_id.id,
                'sale_order_line_id': so_line.id,
            }
        return {}

    def _sale_order_ticket_type_change_notify(self, new_event_ticket):
        fallback_user_id = self.env.user.id if not self.env.user._is_public() else self.env.ref("base.user_admin").id
        for registration in self:
            render_context = {
                'registration': registration,
                'old_ticket_name': registration.event_ticket_id.name,
                'new_ticket_name': new_event_ticket.name
            }
            user_id = registration.event_id.user_id.id or registration.sale_order_id.user_id.id or fallback_user_id
            registration.sale_order_id._activity_schedule_with_view(
                'mail.mail_activity_data_warning',
                user_id=user_id,
                views_or_xmlid='event_sale.event_ticket_id_change_exception',
                render_context=render_context)

    def _get_registration_summary(self):
        res = super(EventRegistration, self)._get_registration_summary()
        res.update({
            'sale_status': self.sale_status,
            'sale_status_value': self.sale_status and dict(self._fields['sale_status']._description_selection(self.env))[self.sale_status],
            'has_to_pay': self.sale_status == 'to_pay',
        })
        return res

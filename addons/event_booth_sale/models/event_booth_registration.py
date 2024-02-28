# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class EventBoothRegistration(models.Model):
    """event.booth.registrations are used to allow multiple partners to book the same booth.
    Whenever a partner has paid their registration all the others linked to the booth will be deleted."""

    _name = 'event.booth.registration'
    _description = 'Event Booth Registration'

    sale_order_line_id = fields.Many2one('sale.order.line', string='Sale Order Line', required=True, ondelete='cascade')
    event_booth_id = fields.Many2one('event.booth', string='Booth', required=True)
    partner_id = fields.Many2one(
        'res.partner', related='sale_order_line_id.order_partner_id', store=True)
    contact_name = fields.Char(string='Contact Name', compute='_compute_contact_name', readonly=False, store=True)
    contact_email = fields.Char(string='Contact Email', compute='_compute_contact_email', readonly=False, store=True)
    contact_phone = fields.Char(string='Contact Phone', compute='_compute_contact_phone', readonly=False, store=True)
    contact_mobile = fields.Char(string='Contact Mobile', compute='_compute_contact_mobile', readonly=False, store=True)

    _sql_constraints = [('unique_registration', 'unique(sale_order_line_id, event_booth_id)',
                         'There can be only one registration for a booth by sale order line')]

    @api.depends('partner_id')
    def _compute_contact_name(self):
        for registration in self:
            if not registration.contact_name:
                registration.contact_name = registration.partner_id.name or False

    @api.depends('partner_id')
    def _compute_contact_email(self):
        for registration in self:
            if not registration.contact_email:
                registration.contact_email = registration.partner_id.email or False

    @api.depends('partner_id')
    def _compute_contact_phone(self):
        for registration in self:
            if not registration.contact_phone:
                registration.contact_phone = registration.partner_id.phone or False

    @api.depends('partner_id')
    def _compute_contact_mobile(self):
        for registration in self:
            if not registration.contact_mobile:
                registration.contact_mobile = registration.partner_id.mobile or False

    @api.model
    def _get_fields_for_booth_confirmation(self):
        return ['sale_order_line_id', 'partner_id', 'contact_name', 'contact_email', 'contact_phone', 'contact_mobile']

    def action_confirm(self):
        for registration in self:
            values = {
                field: registration[field].id if isinstance(registration[field], models.BaseModel) else registration[field]
                for field in self._get_fields_for_booth_confirmation()
            }
            registration.event_booth_id.action_confirm(values)
        self._cancel_pending_registrations()

    def _cancel_pending_registrations(self):
        body = '<p>%(message)s: <ul>%(booth_names)s</ul></p>' % {
            'message': _('Your order has been cancelled because the following booths have been reserved'),
            'booth_names': ''.join('<li>%s</li>' % booth.display_name for booth in self.event_booth_id)
        }
        other_registrations = self.search([
            ('event_booth_id', 'in', self.event_booth_id.ids),
            ('id', 'not in', self.ids)
        ])
        for order in other_registrations.sale_order_line_id.order_id:
            order.sudo().message_post(
                body=body,
                partner_ids=order.user_id.partner_id.ids,
            )
            order.sudo()._action_cancel()
        other_registrations.unlink()

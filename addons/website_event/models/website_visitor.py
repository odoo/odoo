# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain


class WebsiteVisitor(models.Model):
    _inherit = 'website.visitor'

    event_registration_ids = fields.One2many(
        'event.registration', 'visitor_id', string='Event Registrations',
        groups="event.group_event_registration_desk")
    event_registration_count = fields.Integer(
        '# Registrations', compute='_compute_event_registration_count',
        groups="event.group_event_registration_desk")
    event_registered_ids = fields.Many2many(
        'event.event', string="Registered Events",
        compute="_compute_event_registered_ids", compute_sudo=True,
        search="_search_event_registered_ids",
        groups="event.group_event_registration_desk")

    @api.depends('partner_id', 'event_registration_ids.name')
    def _compute_display_name(self):
        """ If there is an event registration for an anonymous visitor, use that
        registered attendee name as visitor name. """
        super()._compute_display_name()
        # sudo is needed for `event_registration_ids`
        for visitor in self.sudo().filtered(lambda v: not v.partner_id and v.event_registration_ids):
            visitor.display_name = visitor.event_registration_ids[-1].name

    @api.depends('event_registration_ids')
    def _compute_event_registration_count(self):
        read_group_res = self.env['event.registration']._read_group(
            [('visitor_id', 'in', self.ids)],
            ['visitor_id'], ['__count'])
        visitor_mapping = {visitor.id: count for visitor, count in read_group_res}
        for visitor in self:
            visitor.event_registration_count = visitor_mapping.get(visitor.id, 0)

    @api.depends('event_registration_ids.email', 'event_registration_ids.phone')
    def _compute_email_phone(self):
        super(WebsiteVisitor, self)._compute_email_phone()

        for visitor in self.filtered(lambda visitor: not visitor.email or not visitor.mobile):
            linked_registrations = visitor.event_registration_ids.sorted(lambda reg: (reg.create_date, reg.id), reverse=False)
            if not visitor.email:
                visitor.email = next((reg.email for reg in linked_registrations if reg.email), False)
            if not visitor.mobile:
                visitor.mobile = next((reg.phone for reg in linked_registrations if reg.phone), False)

    @api.depends('event_registration_ids')
    def _compute_event_registered_ids(self):
        # include parent's registrations in a visitor o2m field. We don't add
        # child one as child should not have registrations (moved to the parent)
        for visitor in self:
            all_registrations = visitor.event_registration_ids
            visitor.event_registered_ids = all_registrations.mapped('event_id')

    def _search_event_registered_ids(self, operator, operand):
        """ Search visitors with terms on events within their event registrations. E.g. [('event_registered_ids',
        'in', [1, 2])] should return visitors having a registration on events 1, 2 as
        well as their children for notification purpose. """
        if operator in ('not in', 'not any'):
            raise UserError(self.env._("Unsupported 'Not In' operation on visitors registrations"))

        all_registrations = self.env['event.registration'].sudo().search([
            ('event_id', operator, operand)
        ])
        if all_registrations:
            visitor_ids = all_registrations.with_context(active_test=False).visitor_id.ids
        else:
            visitor_ids = []

        return [('id', 'in', visitor_ids)]

    def _inactive_visitors_domain(self):
        """ Visitors registered to events are considered always active and should not be deleted. """
        return super()._inactive_visitors_domain() & Domain('event_registration_ids', '=', False)

    def _merge_visitor(self, target):
        """ Override linking process to link registrations to the final visitor. """
        self.event_registration_ids.visitor_id = target.id
        registration_wo_partner = self.event_registration_ids.filtered(lambda registration: not registration.partner_id)
        if registration_wo_partner:
            registration_wo_partner.partner_id = target.partner_id
        return super()._merge_visitor(target)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class WebsiteVisitor(models.Model):
    _name = 'website.visitor'
    _inherit = ['website.visitor']

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

    @api.depends('event_registration_ids')
    def _compute_event_registration_count(self):
        if self.ids:
            read_group_res = self.env['event.registration'].read_group(
                [('visitor_id', 'in', self.ids)],
                ['visitor_id'], ['visitor_id'])
            visitor_mapping = dict(
                (item['visitor_id'][0], item['visitor_id_count'])
                for item in read_group_res)
        else:
            visitor_mapping = dict()
        for visitor in self:
            visitor.event_registration_count = visitor_mapping.get(visitor.id) or 0

    @api.depends('event_registration_ids.email', 'event_registration_ids.mobile', 'event_registration_ids.phone')
    def _compute_email_phone(self):
        super(WebsiteVisitor, self)._compute_email_phone()
        self.flush()

        for visitor in self.filtered(lambda visitor: not visitor.email or not visitor.mobile):
            linked_registrations = visitor.event_registration_ids.sorted(lambda reg: (reg.create_date, reg.id), reverse=False)
            if not visitor.email:
                visitor.email = next((reg.email for reg in linked_registrations if reg.email), False)
            if not visitor.mobile:
                visitor.mobile = next((reg.mobile or reg.phone for reg in linked_registrations if reg.mobile or reg.phone), False)

    @api.depends('parent_id', 'event_registration_ids')
    def _compute_event_registered_ids(self):
        # include parent's registrations in a visitor o2m field. We don't add
        # child one as child should not have registrations (moved to the parent)
        for visitor in self:
            all_registrations = visitor.event_registration_ids | visitor.parent_id.event_registration_ids
            visitor.event_registered_ids = all_registrations.mapped('event_id')

    def _search_event_registered_ids(self, operator, operand):
        """ Search visitors with terms on events within their event registrations. E.g. [('event_registered_ids',
        'in', [1, 2])] should return visitors having a registration on events 1, 2 as
        well as their children for notification purpose. """
        if operator == "not in":
            raise NotImplementedError("Unsupported 'Not In' operation on visitors registrations")

        all_registrations = self.env['event.registration'].sudo().search([
            ('event_id', operator, operand)
        ])
        if all_registrations:
            # search children, even archived one, to contact them
            visitors = all_registrations.with_context(active_test=False).mapped('visitor_id')
            children = self.env['website.visitor'].with_context(
                active_test=False
            ).sudo().search([('parent_id', 'in', visitors.ids)])
            visitor_ids = (visitors + children).ids
        else:
            visitor_ids = []

        return [('id', 'in', visitor_ids)]

    def _link_to_partner(self, partner, update_values=None):
        """ Propagate partner update to registration records """
        if partner:
            registration_wo_partner = self.event_registration_ids.filtered(lambda registration: not registration.partner_id)
            if registration_wo_partner:
                registration_wo_partner.partner_id = partner
        super(WebsiteVisitor, self)._link_to_partner(partner, update_values=update_values)

    def _link_to_visitor(self, target):
        """ Override linking process to link registrations to the final visitor. """
        self.event_registration_ids.write({'visitor_id': target.id})

        return super(WebsiteVisitor, self)._link_to_visitor(target)

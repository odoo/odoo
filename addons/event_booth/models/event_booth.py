# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.osv import expression


class EventBooth(models.Model):
    _name = 'event.booth'
    _description = 'Event Booth'
    _inherit = [
        'event.type.booth',
        'mail.thread',
        'mail.activity.mixin'
    ]

    # owner
    event_type_id = fields.Many2one(ondelete='set null', required=False)
    event_id = fields.Many2one('event.event', string='Event', ondelete='cascade', required=True)
    # customer
    partner_id = fields.Many2one('res.partner', string='Renter', tracking=True, copy=False)
    contact_name = fields.Char('Renter Name', compute='_compute_contact_name', readonly=False, store=True, copy=False)
    contact_email = fields.Char('Renter Email', compute='_compute_contact_email', readonly=False, store=True, copy=False)
    contact_mobile = fields.Char('Renter Mobile', compute='_compute_contact_mobile', readonly=False, store=True, copy=False)
    contact_phone = fields.Char('Renter Phone', compute='_compute_contact_phone', readonly=False, store=True, copy=False)
    # state
    state = fields.Selection(
        [('available', 'Available'), ('unavailable', 'Unavailable')],
        string='Status', group_expand='_group_expand_states',
        default='available', required=True, tracking=True)
    is_available = fields.Boolean(compute='_compute_is_available', search='_search_is_available')

    @api.depends('partner_id')
    def _compute_contact_name(self):
        for booth in self:
            if not booth.contact_name:
                booth.contact_name = booth.partner_id.name or False

    @api.depends('partner_id')
    def _compute_contact_email(self):
        for booth in self:
            if not booth.contact_email:
                booth.contact_email = booth.partner_id.email or False

    @api.depends('partner_id')
    def _compute_contact_mobile(self):
        for booth in self:
            if not booth.contact_mobile:
                booth.contact_mobile = booth.partner_id.mobile or False

    @api.depends('partner_id')
    def _compute_contact_phone(self):
        for booth in self:
            if not booth.contact_phone:
                booth.contact_phone = booth.partner_id.phone or False

    @api.depends('state')
    def _compute_is_available(self):
        for booth in self:
            booth.is_available = booth.state == 'available'

    def _search_is_available(self, operator, operand):
        negative = operator in expression.NEGATIVE_TERM_OPERATORS
        if (negative and operand) or not operand:
            return [('state', '=', 'unavailable')]
        return [('state', '=', 'available')]

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.model_create_multi
    def create(self, vals_list):
        res = super(EventBooth, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        unavailable_booths = res.filtered(lambda booth: not booth.is_available)
        unavailable_booths._post_confirmation_message()
        return res

    def write(self, vals):
        to_confirm = self.filtered(lambda booth: booth.state == 'available')
        wpartner = {}
        if 'state' in vals or 'partner_id' in vals:
            wpartner = dict(
                (booth, booth.partner_id.ids)
                for booth in self.filtered(lambda booth: booth.partner_id)
            )

        res = super(EventBooth, self).write(vals)

        if vals.get('state') == 'unavailable' or vals.get('partner_id'):
            for booth in self:
                booth.message_subscribe(booth.partner_id.ids)
        for booth in self:
            if wpartner.get(booth) and booth.partner_id.id not in wpartner[booth]:
                booth.message_unsubscribe(wpartner[booth])

        if vals.get('state') == 'unavailable':
            to_confirm._action_post_confirm(vals)

        return res

    def _post_confirmation_message(self):
        for booth in self:
            booth.event_id.message_post_with_view(
                'event_booth.event_booth_booked_template',
                values={
                    'booth': booth,
                },
                subtype_id=self.env.ref('event_booth.mt_event_booth_booked').id,
            )

    def action_confirm(self, additional_values=None):
        write_vals = dict({'state': 'unavailable'}, **additional_values or {})
        self.write(write_vals)

    def _action_post_confirm(self, write_vals):
        self._post_confirmation_message()

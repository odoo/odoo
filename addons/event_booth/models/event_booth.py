# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


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
    partner_id = fields.Many2one('res.partner', string='Renter', tracking=True)
    partner_name = fields.Char('Renter Name', compute='_compute_partner_name', readonly=False, store=True)
    partner_email = fields.Char('Renter Email', compute='_compute_partner_email', readonly=False, store=True)
    partner_phone = fields.Char(string='Renter Phone', compute='_comptue_partner_phone', readonly=False, store=True)
    # state
    state = fields.Selection(
        [('available', 'Available'), ('unavailable', 'Unavailable')],
        string='Status', group_expand='_group_expand_states',
        help='Shows the availability of a Booth')
    is_available = fields.Boolean(compute='_compute_is_available', search='_search_is_available')

    @api.depends('partner_id')
    def _compute_partner_name(self):
        for booth in self:
            if not booth.partner_name:
                booth.partner_name = booth.partner_id.name or False

    @api.depends('partner_id')
    def _compute_partner_email(self):
        for booth in self:
            if not booth.partner_email:
                booth.partner_email = booth.partner_id.email or False

    @api.depends('partner_id')
    def _comptue_partner_phone(self):
        for booth in self:
            if not booth.partner_phone:
                booth.partner_phone = booth.partner_id.phone or False

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

    @api.depends('state')
    def _compute_is_available(self):
        for booth in self:
            booth.is_available = booth.state == 'available'

    def _search_is_available(self, operator, operand):
        # TDE TODO
        return []
    @api.model_create_multi
    def create(self, vals_list):
        return super(EventBooth, self.with_context(mail_create_nosubscribe=True)).create(vals_list)

    def write(self, vals):
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
            if wpartner.get(booth) and booth.partner_id.id != wpartner[booth]:
                booth.message_unsubscribe(wpartner[booth])

        if vals.get('state') == 'unavailable':
            self._post_confirmation_message()

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

    def action_confirm(self, values):
        values.update({'state': 'unavailable'})
        self.write(values)

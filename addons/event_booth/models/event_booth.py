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
    partner_id = fields.Many2one(
        'res.partner', string='Renter', compute='_compute_partner_id',
        readonly=False, store=True, tracking=True)
    partner_name = fields.Char(related='partner_id.name', string='Renter Name')
    partner_email = fields.Char(related='partner_id.email', string='Renter Email')
    partner_phone = fields.Char(related='partner_id.phone', string='Renter Phone')
    # state
    # TDE TODO: not sure but probably some update to do with state and partner -> reset not mandatory ?
    state = fields.Selection([
        ('available', 'Available'),
        ('unavailable', 'Unavailable'),
    ], string='Status', compute='_compute_state', readonly=False, store=True,
       group_expand='_group_expand_states', help='Shows the availability of a Booth')
    is_available = fields.Boolean(compute='_compute_is_available', search='_search_is_available')

    @api.depends('partner_id')
    def _compute_state(self):
        for booth in self:
            booth.state = 'unavailable' if booth.partner_id else 'available'

    @api.depends('state')
    def _compute_is_available(self):
        for booth in self:
            booth.is_available = booth.state == 'available'

    def _search_is_available(self, operator, operand):
        # TDE TODO
        return []

    @api.depends('state')
    def _compute_partner_id(self):
        for booth in self:
            if booth.state == 'available':
                booth.partner_id = False
            elif booth.state == 'unavailable' and not booth.partner_id:
                booth.partner_id = self.env.user.partner_id.id

    def _group_expand_states(self, states, domain, order):
        return [key for key, val in type(self).state.selection]

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

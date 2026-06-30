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
    event_id = fields.Many2one('event.event', string='Event', ondelete='cascade', required=True, index=True)
    # customer
    partner_id = fields.Many2one('res.partner', string='Renter', tracking=True, copy=False)
    contact_name = fields.Char('Renter Name', compute='_compute_contact_name', readonly=False, store=True, copy=False)
    contact_email = fields.Char('Renter Email', compute='_compute_contact_email', readonly=False, store=True, copy=False)
    contact_phone = fields.Char('Renter Phone', compute='_compute_contact_phone', readonly=False, store=True, copy=False)
    # state
    state = fields.Selection(
        [('available', 'Available'), ('unavailable', 'Unavailable')],
        string='Status', group_expand=True,
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
    def _compute_contact_phone(self):
        for booth in self:
            if not booth.contact_phone:
                booth.contact_phone = booth.partner_id.phone or False

    @api.depends('state')
    def _compute_is_available(self):
        for booth in self:
            booth.is_available = booth.state == 'available'

    def _search_is_available(self, operator, value):
        if operator not in ('in', 'not in'):
            return NotImplemented
        return [('state', '=', 'available' if operator == 'in' else 'unavailable')]

    @api.model_create_multi
    def create(self, vals_list):
        res = super(EventBooth, self.with_context(mail_create_nosubscribe=True)).create(vals_list)
        unavailable_booths = res.filtered(lambda booth: not booth.is_available)
        unavailable_booths._post_confirmation_message()
        return res

    def write(self, vals):
        to_confirm = self.filtered(lambda booth: booth.state == 'available')
        res = super(EventBooth, self).write(vals)
        if vals.get('state') == 'unavailable':
            to_confirm._action_post_confirm(vals)
        return res

    def _post_confirmation_message(self):
        for booth in self:
            booth.event_id.message_post_with_source(
                'event_booth.event_booth_booked_template',
                render_values={
                    'booth': booth,
                },
                subtype_xmlid='event_booth.mt_event_booth_booked',
            )

    def action_confirm(self, additional_values=None):
        write_vals = dict({'state': 'unavailable'}, **additional_values or {})
        self.write(write_vals)

    def _action_post_confirm(self, write_vals):
        self._post_confirmation_message()

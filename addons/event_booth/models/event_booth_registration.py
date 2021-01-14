# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class EventBoothRegistration(models.Model):
    _name = 'event.booth.registration'
    _description = 'Event Booth Registration'
    _order = 'partner_id asc'

    booth_slot_ids = fields.Many2many(
        'event.booth.slot', 'event_booth_slot_booth_registration_rel',
        'booth_registration_id', 'booth_slot_id',
        string='Booth Slot')
    partner_id = fields.Many2one(
        'res.partner', string='Booked By', required=True)
    name = fields.Char(string='Topic')
    contact_name = fields.Char(
        string='Contact Name', compute='_compute_contact_name', readonly=False, store=True)
    contact_email = fields.Char(
        string='Contact Email', compute='_compute_contact_email', readonly=False, store=True)
    contact_phone = fields.Char(
        string='Contact Phone', compute='_compute_contact_phone', readonly=False, store=True)
    contact_mobile = fields.Char(
        string='Contact Mobile', compute='_compute_contact_mobile', readonly=False, store=True)
    state = fields.Selection([
        ('draft', 'Unconfirmed'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Cancelled')],
        string='Status', default='draft', )
    confirmation_date = fields.Datetime(string='Confirmation Date')
    confirmation_user_id = fields.Many2one('res.users', string='Confirmed By')

    def _contact_not_set(self):
        self.ensure_one()
        return not self._origin.contact_name and not self._origin.contact_email \
               and not self._origin.contact_phone and not self._origin.contact_mobile

    @api.depends('partner_id')
    def _compute_contact_name(self):
        for registration in self:
            if registration._contact_not_set():
                registration.contact_name = registration.partner_id.name

    @api.depends('partner_id')
    def _compute_contact_email(self):
        for registration in self:
            if registration._contact_not_set():
                registration.contact_email = registration.partner_id.email

    @api.depends('partner_id')
    def _compute_contact_phone(self):
        for registration in self:
            if registration._contact_not_set():
                registration.contact_phone = registration.partner_id.phone

    @api.depends('partner_id')
    def _compute_contact_mobile(self):
        for registration in self:
            if registration._contact_not_set():
                registration.contact_mobile = registration.partner_id.mobile

    def action_confirm(self):
        self.ensure_one()
        self.booth_slot_ids.action_confirm(self)
        self.write({
            'state': 'confirm',
            'confirmation_date': fields.Datetime.now(),
            'confirmation_user_id': self.env.user.id,
        })

    def action_set_draft(self):
        self.write({'state': 'draft'})

    def action_cancel(self):
        self.ensure_one()
        self.booth_slot_ids.action_cancel()
        self.write({
            'state': 'cancel',
        })

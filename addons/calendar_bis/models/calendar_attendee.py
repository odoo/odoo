import uuid
from odoo import models, fields, api


class CalendarAttendee(models.Model):
    _name = "calendar.attendee_bis"
    _description = "Calendar Attendee"
    _order = "partner_id desc, id"

    def _default_access_token(self):
        return uuid.uuid4().hex

    timeslot_id = fields.Many2one('calendar.timeslot', required=True, ondelete='cascade', copy=False)
    partner_id = fields.Many2one('res.partner')
    email = fields.Char('E-Mail', store=True, compute='_compute_email', copy=True)
    display_name = fields.Char(string='Display Name', compute='_compute_display_name')
    access_token = fields.Char('Invitation Token', default=_default_access_token, copy=False)
    state = fields.Selection([
        ('maybe', 'Maybe'),
        ('no', 'No'),
        ('yes', 'Yes'),
    ], string='Status', default='maybe', copy=False)

    _sql_constraints = [
        ('has_attendee', 'check(partner_id IS NOT NULL OR email IS NOT NULL)', 'The attendee should be linked to an email or an user'),
    ]

    def _compute_display_name(self):
        for attendee in self:
            attendee.display_name = attendee.partner_id.display_name or attendee.email

    def _compute_email(self):
        for attendee in self:
            attendee.email = attendee.partner_id.email or attendee.email

    @api.depends('email')
    def _compute_partner_id(self):
        for attendee in self:
            if not attendee.partner_id and attendee.email:
                attendee.partner_id = self.env['res.partner'].search([('email', '=', attendee.email)], limit=1)

    def do_accept(self):
        return self.write({'state': 'yes'})

    def do_decline(self):
        return self.write({'state': 'no'})


class CalendarAttendeeMail(models.TransientModel):
    _name = "calendar.attendee_bis.mail"
    _description = "Calendar Attendee Mail"

    name = fields.Char('E-Mail')

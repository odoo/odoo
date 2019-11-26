# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import uuid
import base64

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class Attendee(models.Model):
    """ Calendar Attendee Information """

    _name = 'calendar.attendee'
    _rec_name = 'common_name'
    _description = 'Calendar Attendee Information'

    def _default_access_token(self):
        return uuid.uuid4().hex

    STATE_SELECTION = [
        ('needsAction', 'Needs Action'),
        ('tentative', 'Uncertain'),
        ('declined', 'Declined'),
        ('accepted', 'Accepted'),
    ]

    state = fields.Selection(STATE_SELECTION, string='Status', readonly=True, default='needsAction',
                             help="Status of the attendee's participation")
    common_name = fields.Char('Common name', compute='_compute_common_name', store=True)
    partner_id = fields.Many2one('res.partner', 'Contact', readonly=True)
    email = fields.Char('Email', help="Email of Invited Person")
    availability = fields.Selection([('free', 'Free'), ('busy', 'Busy')], 'Free/Busy', readonly=True)
    access_token = fields.Char('Invitation Token', default=_default_access_token)
    event_id = fields.Many2one('calendar.event', 'Meeting linked', ondelete='cascade')

    @api.depends('partner_id', 'partner_id.name', 'email')
    def _compute_common_name(self):
        for attendee in self:
            attendee.common_name = attendee.partner_id.name or attendee.email

    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        """ Make entry on email and availability on change of partner_id field. """
        self.email = self.partner_id.email

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if not values.get("email") and values.get("common_name"):
                common_nameval = values.get("common_name").split(':')
                email = [x for x in common_nameval if '@' in x] # TODO JEM : should be refactored
                values['email'] = email and email[0] or ''
                values['common_name'] = values.get("common_name")
        return super(Attendee, self).create(vals_list)

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        raise UserError(_('You cannot duplicate a calendar attendee.'))

    def _send_mail_to_attendees(self, template_xmlid, force_send=False, force_event_id=None):
        """ Send mail for event invitation to event attendees.
            :param template_xmlid: xml id of the email template to use to send the invitation
            :param force_send: if set to True, the mail(s) will be sent immediately (instead of the next queue processing)
        """
        res = False

        if self.env['ir.config_parameter'].sudo().get_param('calendar.block_mail') or self._context.get("no_mail_to_attendees"):
            return res

        calendar_view = self.env.ref('calendar.view_calendar_event_calendar')
        invitation_template = self.env.ref(template_xmlid)

        # get ics file for all meetings
        ics_files = force_event_id._get_ics_file() if force_event_id else self.mapped('event_id')._get_ics_file()

        # prepare rendering context for mail template
        colors = {
            'needsAction': 'grey',
            'accepted': 'green',
            'tentative': '#FFFF00',
            'declined': 'red'
        }
        rendering_context = dict(self._context)
        rendering_context.update({
            'color': colors,
            'action_id': self.env['ir.actions.act_window'].search([('view_id', '=', calendar_view.id)], limit=1).id,
            'dbname': self._cr.dbname,
            'base_url': self.env['ir.config_parameter'].sudo().get_param('web.base.url', default='http://localhost:8069'),
            'force_event_id': force_event_id,
        })
        invitation_template = invitation_template.with_context(rendering_context)

        # send email with attachments
        mail_ids = []
        for attendee in self:
            if attendee.email or attendee.partner_id.email:
                # FIXME: is ics_file text or bytes?
                event_id = force_event_id.id if force_event_id else attendee.event_id.id
                ics_file = ics_files.get(event_id)

                email_values = {
                    'model': None,  # We don't want to have the mail in the tchatter while in queue!
                    'res_id': None,
                }
                if ics_file:
                    email_values['attachment_ids'] = [
                        (0, 0, {'name': 'invitation.ics',
                                'mimetype': 'text/calendar',
                                'datas': base64.b64encode(ics_file)})
                    ]
                    mail_ids.append(invitation_template.with_context(no_document=True).send_mail(attendee.id, email_values=email_values, notif_layout='mail.mail_notification_light'))
                else:
                    mail_ids.append(invitation_template.send_mail(attendee.id, email_values=email_values, notif_layout='mail.mail_notification_light'))

        if force_send and mail_ids:
            res = self.env['mail.mail'].browse(mail_ids).send()

        return res

    def do_tentative(self):
        """ Makes event invitation as Tentative. """
        return self.write({'state': 'tentative'})

    def do_accept(self):
        """ Marks event invitation as Accepted. """
        result = self.write({'state': 'accepted'})
        for attendee in self:
            if attendee.event_id:
                attendee.event_id.message_post(body=_("%s has accepted invitation") % (attendee.common_name), subtype_xmlid="calendar.subtype_invitation")
        return result

    def do_decline(self):
        """ Marks event invitation as Declined. """
        res = self.write({'state': 'declined'})
        for attendee in self:
            if attendee.event_id:
                attendee.event_id.message_post(body=_("%s has declined invitation") % (attendee.common_name), subtype_xmlid="calendar.subtype_invitation")
        return res


# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_encode, url_join
from markupsafe import Markup

from odoo import models, fields, api, _, SUPERUSER_ID

class FrontdeskVisitor(models.Model):
    _name = 'frontdesk.visitor'
    _description = 'Frontdesk Visitors'
    _order = 'check_in'

    active = fields.Boolean(default=True)
    name = fields.Char('Name', required=True)
    phone = fields.Char('Phone')
    email = fields.Char('Email')
    company = fields.Char('Visitor Company')
    message = fields.Html()
    host_ids = fields.Many2many('hr.employee', string='Host Name', domain="[('user_id', '!=', False)]")
    drink_ids = fields.Many2many('frontdesk.drink', string='Drinks')
    check_in = fields.Datetime(string='Check In')
    check_out = fields.Datetime(string='Check Out')
    duration = fields.Float('Duration', compute="_compute_duration", store=True, default=1.0)
    state = fields.Selection(string='Status',
        selection=[('planned', 'Planned'),
                   ('checked_in', 'Checked-In'),
                   ('checked_out', 'Checked-Out'),
                   ('canceled', 'Canceled')],
        default='planned'
    )
    station_id = fields.Many2one('frontdesk.frontdesk', required=True)
    visitor_properties = fields.Properties('Properties', definition='station_id.visitor_properties_definition', copy=True)
    served = fields.Boolean(string='Drink Served')

    def write(self, vals):
        if vals.get('state') == 'checked_in':
            vals['check_in'] = fields.Datetime.now()
            self._notify()
            if self.drink_ids:
                self._notify_to_people()
        elif vals.get('state') == 'checked_out':
            vals['check_out'] = fields.Datetime.now()
            vals['served'] = True
        return super().write(vals)

    @api.depends('check_in', 'check_out')
    def _compute_duration(self):
        for visitor in self:
            if visitor.check_in and visitor.check_out:
                visitor.duration = (visitor.check_out - visitor.check_in).total_seconds() / 3600

    def action_check_in(self):
        self.ensure_one()
        self.state = 'checked_in'

    def action_canceled(self):
        self.ensure_one()
        self.state = 'canceled'

    def action_check_out(self):
        self.ensure_one()
        self.state = 'checked_out'

    def action_served(self):
        self.ensure_one()
        self.served = True

    def _notify(self):
        """ Send a notification to the frontdesk's responsible users and the visitor's hosts when the visitor checks in. """
        for visitor in self:
            msg = ""
            visitor_name = visitor.name
            visitor_name += f" ({visitor.phone})" if visitor.phone else ""
            visitor_name += f" ({visitor.company})" if visitor.company else ""
            if visitor.station_id.responsible_ids:
                if visitor.host_ids:
                    host_info = ', '.join([f'{host.name}' for host in visitor.host_ids])
                    msg = visitor.station_id.name + _(" Check-In: %s to meet %s", visitor_name, host_info)
                else:
                    msg = visitor.station_id.name + _(" Check-In: %s", visitor_name)
                visitor._notify_by_discuss(visitor.station_id.responsible_ids, msg)
            if visitor.station_id.host_selection and visitor.host_ids:
                if visitor.station_id.notify_discuss:
                    msg = _("%s just checked-in.", visitor_name)
                    visitor._notify_by_discuss(visitor.host_ids, msg, True)
                if visitor.station_id.notify_email:
                    visitor._notify_by_email()
                if visitor.station_id.notify_sms:
                    visitor._notify_by_sms()

    def _notify_to_people(self):
        """ Send notification to the drink's responsible users when the visitor checks in. """
        for visitor in self:
            if visitor.drink_ids.notify_user_ids:
                action = visitor.env.ref('frontdesk.action_frontdesk_visitor').id
                url = url_encode({
                    'id': visitor.id,
                    'action': action,
                    'model': 'frontdesk.visitor',
                    'view_type': 'form',
                })
                name = f"{self.name} ({self.company})" if self.company else self.name
                msg = _("%(name)s just checked-in. Requested Drink: %(drink)s.",
                    name=Markup('<a href="%s">%s</a>') % (url_join(visitor.get_base_url(), '/web?#%s' % url), name),
                    drink=', '.join(drink.name for drink in visitor.drink_ids),
                )
                visitor._notify_by_discuss(visitor.drink_ids.notify_user_ids, msg)

    def _notify_by_discuss(self, recipients, msg, is_host=False):
        for recipient in recipients:
            odoobot_id = self.env.ref("base.partner_root").id
            partners_to = [recipient.user_partner_id.id] if is_host else [recipient.partner_id.id]
            channel = self.env["discuss.channel"].with_user(SUPERUSER_ID).channel_get(partners_to)
            channel.message_post(body=msg, author_id=odoobot_id, message_type="comment", subtype_xmlid="mail.mt_comment")

    def _notify_by_email(self):
        for host in self.host_ids:
            if host.work_email:
                odoobot = self.env.ref('base.partner_root')
                mail_template = self.station_id.mail_template_id
                ctx = {'host_name': host.name, 'lang': host.user_partner_id.lang}
                body = mail_template.with_context(ctx)._render_field('body_html', self.ids, compute_lang=True)[self.id]
                subject = mail_template.with_context(ctx)._render_field('subject', self.ids, compute_lang=True)[self.id]
                host.message_notify(
                    email_from=odoobot.email_formatted,
                    author_id=self.env.user.partner_id.id,
                    body=body,
                    subject=subject,
                    partner_ids=host.user_partner_id.ids,
                    email_layout_xmlid='mail.mail_notification_light',
                    force_send=True,
                )

    def _notify_by_sms(self):
        for host in self.host_ids:
            if host.work_phone:
                odoobot_id = self.env['ir.model.data']._xmlid_to_res_id("base.partner_root")
                sms_template = self.station_id.sms_template_id
                body = sms_template._render_field('body', self.ids, compute_lang=True)[self.id]
                host._message_sms(
                    author_id=odoobot_id,
                    body=body,
                    partner_ids=host.user_partner_id.ids,
                )

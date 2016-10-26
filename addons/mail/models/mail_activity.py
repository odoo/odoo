# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT

# If date_action is more than DUE_DAYS days, display the DATE
# else `Due in X days`
DUE_DAYS = 15

class MailActivity(models.Model):
    _name = 'mail.activity'
    _description = 'Mail Activity'
    _inherits = {'mail.message.subtype': 'subtype_id'}
    _rec_name = 'name'
    _order = "sequence"

    days = fields.Integer('Number of days', default=0,
                          help='Number of days before executing the action, allowing you to plan the date of the action.')
    subtype_id = fields.Many2one('mail.message.subtype', string='Message Subtype', required=True, ondelete='cascade')
    icon = fields.Char(string="Activity Icon", help="Font awesome icon. eg. fa-tasks", groups="base.group_no_one")
    model_id = fields.Many2one('ir.model', string='Related Document Model', groups="base.group_no_one")

    # setting a default value on inherited fields is a bit involved
    internal = fields.Boolean('Internal Only', related='subtype_id.internal', inherited=True, default=True)
    default = fields.Boolean('Default', related='subtype_id.default', inherited=True, default=False)


class MailActivityLog(models.Model):
    _name = "mail.activity.log"
    _description = "Log an Activity"
    _order = "create_date desc"
    _rec_name = 'title_action'

    res_id = fields.Integer('Related Document ID', index=True)
    res_name = fields.Char('Activity Record Name', help="Display name of the related document.")
    model = fields.Char('Related Document Model', index=True)
    next_activity_id = fields.Many2one('mail.activity', string='Activity',
                                       domain="['|', ('model_id', '=', False), ('model_id.model', '=', model)]")
    icon = fields.Char(related="next_activity_id.icon")
    title_action = fields.Char('Summary')
    note = fields.Html(string="Internal Log Notes")
    date_action = fields.Date('Due Date', required=True, index=True, default=fields.Date.today)
    state = fields.Selection([('overdue', 'Overdue'), ('today', 'Today'), ('planned', 'Planned')],
                             compute="_compute_state", default="planned")
    user_id = fields.Many2one('res.users', string='Assigned to', default=lambda self: self.env.user)

    def _compute_state(self):
        today = date.today()
        for record in self:
            date_action = fields.Date.from_string(record.date_action)
            diff = (date_action - today)
            if diff.days == 0:
                record.state = 'today'
            elif diff.days < 0:
                record.state = 'overdue'
            else:
                record.state = 'planned'

    @api.onchange('next_activity_id')
    def _onchange_next_activity_id(self):
        self.title_action = self.next_activity_id.description
        if self.next_activity_id.days:
            self.date_action = (datetime.now() + timedelta(days=self.next_activity_id.days))

    @api.model
    def create(self, vals):
        res_id = vals.get('res_id')
        model = vals.get('model')
        vals['res_name'] = self.env[model].browse(res_id).display_name
        activity_log = super(MailActivityLog, self).create(vals)
        if 'user_id' in vals and vals['user_id'] != self.env.uid:
            activity_log._send_mail()
        return activity_log

    @api.multi
    def write(self, vals):
        logs = super(MailActivityLog, self).write(vals)
        if 'user_id' in vals:
            self._send_mail()
        return logs

    def _send_mail(self):
        for log in self:
            record = self.env[log.model].browse(log.res_id)
            record.with_context(mail_post_autofollow=True).message_post_with_view('mail.message_activity_assigned',
                values={'self': log}, partner_ids=log.user_id.partner_id.ids)

    @api.multi
    def mark_as_done(self):
        msg_id = None
        for log in self:
            body_html = _("""
                <div>
                    <strong>%(name)s <i>%(title_action)s</i></strong>
                    <br />
                    %(note)s
                </div> """) % {
                    'name': log.next_activity_id.name,
                    'title_action': log.title_action and '- %s' % log.title_action or '',
                    'note': log.note or '',
                }
            msg_id = self.env[log.model].browse(log.res_id).message_post(
                body_html, subject=log.title_action, subtype_id=log.next_activity_id.subtype_id.id).id
        # Because activity already logged in chatter
        self.unlink()
        return msg_id

    @api.multi
    def remove_activity_log(self):
        return self.unlink()

    @api.multi
    def action_close_dialog(self):
        return {'type': 'ir.actions.act_window_close'}

    @api.model
    def fetch_activity_logs(self, res_id, model, limit=None):
        activity_logs = self.search_read(domain=[('res_id', '=', res_id), ('model', '=', model)],
                                         fields=[], limit=limit, order="date_action")
        lang_code = self.env.user.lang
        date_format = self.env['res.lang']._lang_get(lang_code).date_format
        today = fields.Date.from_string(fields.Date.today())
        for log in activity_logs:
            diff = (today - fields.Date.from_string(log['date_action'])).days
            if diff > 0:
                day = _("Yesterday") if diff == 1 else _("%d days overdue") % abs(diff)
            elif diff < 0:
                date_action_str = datetime.strptime(log['date_action'], DEFAULT_SERVER_DATE_FORMAT).strftime(date_format.encode('utf-8'))
                day = _("Tomorrow") if diff == -1 else _("Due in %d days") % abs(diff) if diff > - DUE_DAYS else date_action_str
            else:
                day = _("Today")
            log.update({'day': day})
        return activity_logs

    @api.multi
    def action_open_related_document(self):
        self.ensure_one()
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': self.model,
            'type': 'ir.actions.act_window',
            'res_id': self.res_id,
            'context': self.env.context,
        }
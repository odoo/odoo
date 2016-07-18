# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo import api, fields, models, _


class MailActivity(models.Model):
    _name = 'mail.activity'
    _description = 'Mail Activity'
    _inherits = {'mail.message.subtype': 'subtype_id'}
    _rec_name = 'name'
    _order = "sequence"

    days = fields.Integer('Number of days', default=0,
                          help='Number of days before executing the action, allowing you to plan the date of the action.')
    subtype_id = fields.Many2one('mail.message.subtype', string='Message Subtype', required=True, ondelete='cascade')
    icon = fields.Char()

    # setting a default value on inherited fields is a bit involved
    internal = fields.Boolean('Internal Only', related='subtype_id.internal', inherited=True, default=True)
    default = fields.Boolean('Default', related='subtype_id.default', inherited=True, default=False)


class MailActivityLog(models.Model):
    _name = "mail.activity.log"
    _description = "Log an Activity"
    _order = "create_date desc"
    _rec_name = 'title_action'

    res_id = fields.Integer('Related Document ID', index=True)
    record_name = fields.Char('Activity Record Name', help="Display name of the related document.")
    model = fields.Char('Related Document Model', index=True)
    next_activity_id = fields.Many2one('mail.activity', 'Activity')
    icon = fields.Char(related="next_activity_id.icon", default="fa fa-thumb-tack")
    title_action = fields.Char('Summary')
    note = fields.Html()
    date_action = fields.Date('Due Date', required=True, index=True, default=fields.Date.today)
    state = fields.Selection([('overdue', 'Overdue'), ('today', 'Today'), ('planned', 'Planned')],
                             compute="_compute_state", default="planned")

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
    def onchange_next_activity_id(self):
        if not self.title_action:
            self.title_action = self.next_activity_id.description
        if self.next_activity_id.days:
            self.date_action = (datetime.now() + timedelta(days=self.next_activity_id.days))

    @api.multi
    def action_mark_as_done(self):
        msg = None
        for log in self:
            body_html = """
                <div>
                    <p>%(title)s</p>
                    <p><span class='fa %(icon)s' /> %(activity_name)s - <i>%(title_action)s</i></p>
                    <p>%(note)s</p>
                </div> """ % {
                    'title': _('Activity Done'),
                    'icon': log.icon,
                    'activity_name': log.next_activity_id.name,
                    'title_action': log.title_action or '',
                    'note': log.note or '',
                }
            msg = self.env[log.model].browse(log.res_id).message_post(body_html, subject=log.title_action, subtype_id=log.next_activity_id.subtype_id.id)
        # Because activity already logged in chatter
        self.unlink()
        return msg.id

    @api.multi
    def action_remove_activity_log(self):
        if not self:
            return False
        return self.unlink()

    @api.model
    def fetch_activity_logs(self, res_id, model, limit=None):
        activity_logs = self.search_read(domain=[('res_id', '=', res_id), ('model', '=', model)],
                                         fields=[], limit=limit, order="date_action")
        today = fields.Date.from_string(fields.Date.today())
        for log in activity_logs:
            diff = (today - fields.Date.from_string(log['date_action'])).days
            if diff > 0:
                day = _("Yesterday") if diff == 1 else _("%d days overdue") % abs(diff)
            elif diff < 0:
                day = _("Tomorrow") if diff == -1 else _("Due in %d days") % abs(diff)
            else:
                day = _("Today")
            log.update({'day': day})
        return activity_logs

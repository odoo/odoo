# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pytz

from odoo import models, fields, tools, _
from odoo.tools import is_html_empty
from odoo.addons.mail.tools.discuss import Store


class MailActivity(models.Model):
    _inherit = "mail.activity"

    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Meeting", index='btree_not_null', ondelete='cascade')

    def write(self, vals):
        # synchronize calendar events
        res = super().write(vals)
        # protect against loops in case of ill-managed timezones
        if 'date_deadline' in vals and not self.env.context.get('calendar_event_meeting_update') and self.calendar_event_id:
            date_deadline = self[0].date_deadline  # updated, hence all same value
            # also protect against loops in case of ill-managed timezones
            events = self.calendar_event_id.with_context(mail_activity_meeting_update=True)
            user_tz = self.env.context.get('tz') or 'UTC'
            for event in events:
                # allday: just apply diff between dates
                if event.allday and event.start_date != date_deadline:
                    event.start = event.start + (date_deadline - event.start_date)
                # otherwise: we have to check if day did change, based on TZ
                elif not event.allday:
                    # old start in user timezone
                    old_deadline_dt = pytz.utc.localize(event.start).astimezone(pytz.timezone(user_tz))
                    date_diff = date_deadline - old_deadline_dt.date()
                    event.start = event.start + date_diff

        return res

    def action_create_calendar_event(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['context'] = {
            'default_activity_type_id': self.activity_type_id.id,
            'default_res_id': self.env.context.get('default_res_id'),
            'default_res_model': self.env.context.get('default_res_model'),
            'default_name': self.res_name,
            'default_description': self.note if not is_html_empty(self.note) else '',
            'default_activity_ids': [(6, 0, self.ids)],
            'default_partner_ids': self.user_id.partner_id.ids,
            'default_user_id': self.user_id.id,
            'initial_date': self.date_deadline,
            'default_calendar_event_id': self.calendar_event_id.id,
            'orig_activity_ids': self.ids,
            'return_to_parent_breadcrumb': True,
        }
        return action

    def _action_done(self, feedback=False, attachment_ids=False):
        # Add feedback to the internal event 'notes', which is not synchronized with the activity's 'note'
        if feedback:
            for event in self.calendar_event_id:
                notes = event.notes if not tools.is_html_empty(event.notes) else ''
                notes_feedback = _('Feedback: %s', tools.plaintext2html(feedback))
                notes = f'{notes}<br />{notes_feedback}'
                event.write({'notes': notes})
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def unlink_w_meeting(self):
        events = self.mapped('calendar_event_id')
        res = self.unlink()
        events.unlink()
        return res

    def _to_store_defaults(self, target):
        return super()._to_store_defaults(target) + [Store.One("calendar_event_id", [])]

# Part of Odoo. See LICENSE file for full copyright and licensing details.
from ast import literal_eval
from datetime import UTC

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
            for event in events:
                # allday: just apply diff between dates
                if event.allday and event.start_date != date_deadline:
                    event.start = event.start + (date_deadline - event.start_date)
                # otherwise: we have to check if day did change, based on TZ
                elif not event.allday:
                    # old start in user timezone
                    old_deadline_dt = event.start.replace(tzinfo=UTC).astimezone(self.env.tz)
                    date_diff = date_deadline - old_deadline_dt.date()
                    event.start = event.start + date_diff

        return res

    def action_cancel(self):
        res = super().action_cancel()
        return self.check_keep_modal_open_on_activity_actions(res)

    def action_create_calendar_event(self):
        self.ensure_one()
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_calendar_event")
        action['context'] = {
            'default_activity_type_id': self.activity_type_id.id,
            'default_res_id': self.env.context.get('default_res_id'),
            'default_res_model': self.env.context.get('default_res_model'),
            'default_name': self.res_name,
            'default_description': self.note if not is_html_empty(self.note) else '',
            'default_meeting_activity_ids': [(6, 0, self.ids)],
            'default_partner_ids': self.user_id.partner_id.ids,
            'default_user_id': self.user_id.id,
            'initial_date': self.date_deadline,
            'default_calendar_event_id': self.calendar_event_id.id,
            'orig_activity_ids': self.ids,
            'return_to_parent_breadcrumb': True,
        }
        return action

    def action_done(self):
        res = super().action_done()
        return self.check_keep_modal_open_on_activity_actions(res)

    def _action_done(self, feedback=False, attachment_ids=False):
        # Add feedback to the internal event 'notes', which is not synchronized with the activity's 'note'
        if feedback:
            for event in self.calendar_event_id:
                notes = event.notes if not tools.is_html_empty(event.notes) else ''
                notes_feedback = _('Feedback: %s', tools.plaintext2html(feedback))
                notes = f'{notes}<br />{notes_feedback}'
                event.write({'notes': notes})
        return super()._action_done(feedback=feedback, attachment_ids=attachment_ids)

    def action_reschedule_today(self):
        res = super().action_reschedule_today()
        return self.check_keep_modal_open_on_activity_actions(res)

    def action_reschedule_tomorrow(self):
        res = super().action_reschedule_tomorrow()
        return self.check_keep_modal_open_on_activity_actions(res)

    def action_reschedule_nextweek(self):
        res = super().action_reschedule_nextweek()
        return self.check_keep_modal_open_on_activity_actions(res)

    def check_keep_modal_open_on_activity_actions(self, fallback):
        """ Goal: When doing an action in the activities list modal (Done, Reschedule, Cancel),
        instead of closing the modal, keeping it open with the current activities (cf "activity_ids" context key).
        If it's not the case, fallback on expected result.
        Used notably in the user activity list popovers in the calendar view.
        """
        if not self.env.context.get("keep_modal_open_on_activity_actions"):
            return fallback
        action = self.env["ir.actions.actions"]._for_xml_id("calendar.action_mail_activity_view_tree_open_target")
        action_context = literal_eval(action.get("context", "{}"))
        activity_ids = self.env.context.get("activity_ids", [])
        action["domain"] = [("id", "in", activity_ids)]
        action["context"] = {
            **action_context,
            "activity_ids": activity_ids,
        }
        return action

    def unlink_w_meeting(self):
        events = self.mapped('calendar_event_id')
        res = self.unlink()
        events.unlink()
        return res

    def _store_activity_fields(self, res: Store.FieldList):
        super()._store_activity_fields(res)
        res.attr("calendar_event_id")
        res.extend(["res_name"])

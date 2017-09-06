# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools, _


class MailActivityType(models.Model):

    _inherit = "mail.activity.type"

    meeting_type = fields.Selection(selection_add=[('meeting', 'Meeting')])


class MailActivity(models.Model):

    _inherit = "mail.activity"

    activity_meeting_type = fields.Selection(related='activity_type_id.meeting_type')
    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Meeting", ondelete='cascade')

    @api.multi
    def action_create_calendar_event(self):
        self.ensure_one()
        note = tools.html2plaintext(self.note)
        action = {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                        'activity_type_id': self.activity_type_id.id,
                        'default_res_id': self.env.context.get('default_res_id'),
                        'default_res_model': self.env.context.get('default_res_model'),
                        'default_name': self.summary,
                        'default_description': note,
                        'create_activity': True,
                        }
        }
        self.unlink()
        return action

    @api.multi
    def unlink(self):
        for activity in self.filtered('feedback'):
            feedback = tools.html2plaintext(activity.feedback)
            description = activity.calendar_event_id.description
            modify_feedback = (description or '') + "\n" + _("Feedback: ") + feedback
            activity.calendar_event_id.write({'description': modify_feedback})
        return super(MailActivity, self).unlink()

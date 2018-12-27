# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, tools, _


class MailActivityType(models.Model):
    _inherit = "mail.activity.type"

    category = fields.Selection(selection_add=[('meeting', 'Meeting')])


class MailActivity(models.Model):
    _inherit = "mail.activity"

    calendar_event_id = fields.Many2one('calendar.event', string="Calendar Meeting", ondelete='cascade')

    @api.multi
    def action_create_calendar_event(self):
        self.ensure_one()
        action = self.env.ref('calendar.action_calendar_event').read()[0]
        action['context'] = {
            'default_activity_type_id': self.activity_type_id.id,
            'default_res_id': self.env.context.get('default_res_id'),
            'default_res_model': self.env.context.get('default_res_model'),
            'default_name': self.summary or self.res_name,
            'default_description': self.note and tools.html2plaintext(self.note).strip() or '',
            'default_activity_ids': [(6, 0, self.ids)],
        }
        return action

    def action_feedback(self, feedback=False):
        events = self.mapped('calendar_event_id')
        res = super(MailActivity, self).action_feedback(feedback)
        if feedback:
            for event in events:
                description = event.description
                description = '%s\n%s%s' % (description or '', _("Feedback: "), feedback)
                event.write({'description': description})
        return res

    def unlink_w_meeting(self):
        events = self.mapped('calendar_event_id')
        res = self.unlink()
        events.unlink()
        return res

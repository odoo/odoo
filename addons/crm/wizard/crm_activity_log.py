# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, timedelta

from odoo import api, fields, models, tools, _


class ActivityLog(models.TransientModel):

    _name = "crm.activity.log"
    _description = "Log an Activity"
    _rec_name = 'title_action'

    @api.model
    def _default_lead_id(self):
        if 'default_lead_id' in self._context:
            return self._context['default_lead_id']
        if self._context.get('active_model') == 'crm.lead':
            return self._context.get('active_id')
        return False

    next_activity_id = fields.Many2one('crm.activity', 'Activity')
    last_activity_id = fields.Many2one('crm.activity', 'Previous Activity', default=False)
    recommended_activity_id = fields.Many2one("crm.activity", "Recommended Activities")
    title_action = fields.Char('Summary')
    note = fields.Html('Note')
    date_action = fields.Date('Next Activity Date')
    lead_id = fields.Many2one('crm.lead', 'Lead', required=True, default=_default_lead_id)
    team_id = fields.Many2one('crm.team', 'Sales Team')
    date_deadline = fields.Date('Expected Closing')
    planned_revenue = fields.Float('Expected Revenue')

    @api.onchange('lead_id')
    def onchange_lead_id(self):
        self.next_activity_id = self.lead_id.next_activity_id
        self.date_deadline = self.lead_id.date_deadline
        self.team_id = self.lead_id.team_id
        self.planned_revenue = self.lead_id.planned_revenue
        self.title_action = self.lead_id.title_action

    @api.onchange('next_activity_id')
    def onchange_next_activity_id(self):
        if not self.title_action:
            self.title_action = self.next_activity_id.description
        date_action = False
        if self.next_activity_id and self.next_activity_id.days:
            date_action = (datetime.now() + timedelta(days=self.next_activity_id.days)).strftime(tools.DEFAULT_SERVER_DATETIME_FORMAT)
        self.date_action = date_action

    @api.onchange('recommended_activity_id')
    def onchange_recommended_activity_id(self):
        self.next_activity_id = self.recommended_activity_id

    @api.multi
    def action_log_and_schedule(self):
        self.ensure_one()
        self.action_log()
        view_id = self.env.ref('crm.crm_activity_log_view_form_schedule')
        return {
            'name': _('Next activity'),
            'res_model': 'crm.activity.log',
            'context': {
                'default_last_activity_id': self.next_activity_id.id,
                'default_lead_id': self.lead_id.id
            },
            'type': 'ir.actions.act_window',
            'view_id': False,
            'views': [(view_id.id, 'form')],
            'view_mode': 'form',
            'target': 'new',
            'view_type': 'form',
            'res_id': False
        }

    @api.multi
    def action_log(self):
        for log in self:
            body_html = "<div><b>%(title)s</b>: %(next_activity)s</div>%(description)s%(note)s" % {
                'title': _('Activity Done'),
                'next_activity': log.next_activity_id.name,
                'description': log.title_action and '<p><em>%s</em></p>' % log.title_action or '',
                'note': log.note or '',
            }
            log.lead_id.message_post(body_html, subject=log.title_action, subtype_id=log.next_activity_id.subtype_id.id)
            log.lead_id.write({
                'date_deadline': log.date_deadline,
                'planned_revenue': log.planned_revenue,
                'title_action': False,
                'date_action': False,
                'next_activity_id': False,
            })
        return True

    @api.multi
    def action_schedule(self):
        for log in self:
            log.lead_id.write({
                'title_action': log.title_action,
                'date_action': log.date_action,
                'next_activity_id': log.next_activity_id.id,
            })
        return True

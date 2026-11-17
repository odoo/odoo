# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class MailingMailing(models.Model):
    _inherit = 'mailing.mailing'

    participants_count = fields.Integer("Survey Participants Count", compute='_compute_participants_count', groups='survey.group_survey_user')

    def action_view_survey_participants(self):
        action = self.env["ir.actions.actions"]._for_xml_id('survey.action_survey_user_input')
        action['domain'] = [('mass_mailing_id', 'in', self.ids), ('state', '=', 'done')]
        action['context'] = {}
        return action

    def _compute_participants_count(self):
        grouped_participants = dict(self.env["survey.user_input"]._read_group(
            [('mass_mailing_id', 'in', self.ids), ('state', '=', 'done')],
            ['mass_mailing_id'],
            ['__count']))

        for mailing in self:
            mailing.participants_count = grouped_participants.get(mailing, 0)

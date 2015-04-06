# -*- coding: utf-8 -*-

from openerp import api, fields, models, _


class CrmLeadToProjectIssueWizard(models.TransientModel):
    """ wizard to convert a Lead into a Project Issue and move the Mail Thread """
    _name = "crm.lead2projectissue.wizard"
    _inherit = 'crm.partner.binding'

    lead_id = fields.Many2one('crm.lead', string='Lead', domain=[('type', '=', 'lead')], default=lambda self: self.env.context.get('active_id'))
    project_id = fields.Many2one('project.project', string='Project', domain=[('use_issues', '=', True)])

    @api.multi
    def action_lead_to_project_issue(self):
        # get the models
        self.ensure_one()
        Issue = self.env['project.issue']
        # get the lead to transform
        lead = self.lead_id
        partner_id = self._find_matching_partner()
        if not partner_id and (lead.partner_name or lead.contact_name):
            partner_ids = lead.handle_partner_assignation()
            partner_id = partner_ids[lead.id]

        # create new project.issue
        vals = {
            "name": lead.name,
            "description": lead.description,
            "email_from": lead.email_from,
            "project_id": self.project_id.id,
            "partner_id": partner_id,
            "user_id": None
        }
        issue_id = Issue.create(vals).id
        # move the mail thread
        lead.message_change_thread(issue_id, "project.issue")
        # delete the lead
        lead.unlink()
        # return the action to go to the form view of the new Issue
        view_id = self.env.ref('project_issue.project_issue_form_view').id
        return {
            'name': 'Issue created',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'res_id': issue_id,
            'context': self.env.context
        }

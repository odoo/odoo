
from odoo import api, fields, models


class CrmLeadToProjectIssueWizard(models.TransientModel):
    """ wizard to convert a Lead into a Project Issue and move the Mail Thread """

    _name = "crm.lead2projectissue.wizard"
    _inherit = 'crm.partner.binding'

    @api.model
    def default_get(self, fields):
        result = super(CrmLeadToProjectIssueWizard, self).default_get(fields)
        lead_id = self.env.context.get('active_id')
        if lead_id:
            result['lead_id'] = lead_id
        return result

    lead_id = fields.Many2one('crm.lead', string='Lead', domain=[('type', '=', 'lead')])
    project_id = fields.Many2one('project.project', string='Project', domain=[('use_issues', '=', True)])

    @api.multi
    def action_lead_to_project_issue(self):
        self.ensure_one()
        # get the lead to transform
        lead = self.lead_id
        partner_id = self._find_matching_partner()
        if not partner_id and (lead.partner_name or lead.contact_name):
            partner_id = lead.handle_partner_assignation()[lead.id]
        # create new project.issue
        vals = {
            "name": lead.name,
            "description": lead.description,
            "email_from": lead.email_from,
            "project_id": self.project_id.id,
            "partner_id": partner_id,
            "user_id": None
        }
        issue = self.env['project.issue'].create(vals)
        # move the mail thread
        lead.message_change_thread(issue)
        # move attachments
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)])
        attachments.write({'res_model': 'project.issue', 'res_id': issue.id})
        # archive the lead
        lead.write({'active': False})
        # return the action to go to the form view of the new Issue
        view = self.env.ref('project_issue.project_issue_form_view')
        return {
            'name': 'Issue created',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': 'project.issue',
            'type': 'ir.actions.act_window',
            'res_id': issue.id,
            'context': self.env.context
        }

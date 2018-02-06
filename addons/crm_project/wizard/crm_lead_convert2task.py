
from odoo import api, fields, models


class CrmLeadConvert2Task(models.TransientModel):
    """ wizard to convert a Lead into a Project task and move the Mail Thread """

    _name = "crm.lead.convert2task"
    _inherit = 'crm.partner.binding'

    @api.model
    def default_get(self, fields):
        result = super(CrmLeadConvert2Task, self).default_get(fields)
        lead_id = self.env.context.get('active_id')
        if lead_id:
            result['lead_id'] = lead_id
        return result

    lead_id = fields.Many2one('crm.lead', string='Lead', domain=[('type', '=', 'lead')])
    project_id = fields.Many2one('project.project', string='Project')

    @api.multi
    def action_lead_to_project_task(self):
        self.ensure_one()
        # get the lead to transform
        lead = self.lead_id
        partner_id = self._find_matching_partner()
        if not partner_id and (lead.partner_name or lead.contact_name):
            partner_id = lead.handle_partner_assignation()[lead.id]
        # create new project.task
        vals = {
            "name": lead.name,
            "description": lead.description,
            "email_from": lead.email_from,
            "project_id": self.project_id.id,
            "partner_id": partner_id,
            "user_id": None
        }
        task = self.env['project.task'].create(vals)
        # move the mail thread
        lead.message_change_thread(task)
        # move attachments
        attachments = self.env['ir.attachment'].search([('res_model', '=', 'crm.lead'), ('res_id', '=', lead.id)])
        attachments.write({'res_model': 'project.task', 'res_id': task.id})
        # archive the lead
        lead.write({'active': False})
        # return the action to go to the form view of the new Task
        view = self.env.ref('project.view_task_form2')
        return {
            'name': 'Task created',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view.id,
            'res_model': 'project.task',
            'type': 'ir.actions.act_window',
            'res_id': task.id,
            'context': self.env.context
        }

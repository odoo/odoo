# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo import models, fields, api, _


class CreateTask(models.TransientModel):
    _name = 'helpdesk.create.fsm.task'
    _description = 'Create a Field Service task'

    helpdesk_ticket_id = fields.Many2one('helpdesk.ticket', string='Related ticket', required=True)
    company_id = fields.Many2one(related='helpdesk_ticket_id.company_id', export_string_translation=False)
    name = fields.Char('Title', required=True)
    project_id = fields.Many2one('project.project', string='Project', help='Project in which to create the task', required=True, domain="[('company_id', '=', company_id), ('is_fsm', '=', True)]")
    partner_id = fields.Many2one('res.partner', string='Customer', help="Ticket's customer, will be linked to the task", required=True, domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.model
    def default_get(self, fields_list):
        defaults = super(CreateTask, self).default_get(fields_list)
        if 'project_id' in fields_list and not defaults.get('project_id'):
            task_default = self.env['project.task'].with_context(fsm_mode=True).default_get(['project_id'])
            defaults.update({'project_id': task_default.get('project_id', False)})
        partner_id = defaults.get('partner_id')
        if partner_id:
            delivery = self.env['res.partner'].browse(partner_id).address_get(['delivery']).get('delivery')
            if delivery:
                defaults.update({'partner_id': delivery})
        return defaults

    def _generate_task_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'helpdesk_ticket_id': self.helpdesk_ticket_id.id,
            'project_id': self.project_id.id,
            'partner_id': self.partner_id.id,
            'description': self.helpdesk_ticket_id.description,
        }

    def action_generate_task(self):
        self.ensure_one()
        new_task = self.env['project.task'].create(self._generate_task_values())
        self.helpdesk_ticket_id.message_post_with_source(
            'helpdesk.ticket_conversion_link',
            render_values={'created_record': new_task, 'message': _('Task created')},
            subtype_xmlid='mail.mt_note',
        )
        return new_task

    def action_generate_and_view_task(self):
        self.ensure_one()
        new_task = self.action_generate_task()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Tasks from Tickets'),
            'res_model': 'project.task',
            'res_id': new_task.id,
            'view_mode': 'form',
            'view_id': self.env.ref('project.view_task_form2').id,
            'context': {
                'fsm_mode': True,
                'create': False,
            }
        }

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.tests import Form

class TestHelpdeskFsm(HelpdeskCommon):
    def test_helpdesk_fsm(self):
        self.test_team.use_fsm = True

        ticket = self.env['helpdesk.ticket'].create({
            'name': 'test',
            'partner_id': self.partner.id,
            'team_id': self.test_team.id,
        })

        task_form = Form(self.env['helpdesk.create.fsm.task'].with_context(default_helpdesk_ticket_id=ticket.id))
        task_form.name = ticket.name
        task_form.partner_id = self.partner
        task = task_form.save().action_generate_task()

        self.assertTrue(task.is_fsm, 'The created task should be in an fsm project.')
        self.assertEqual(task.name, ticket.name, 'The created task should have the same name as the ticket.')
        self.assertEqual(task.partner_id, ticket.partner_id, 'The created task should have the same customer as the ticket.')
        self.assertEqual(task.helpdesk_ticket_id, ticket, 'The created task should be linked to the ticket.')

        task.action_fsm_validate()
        last_message = ticket.message_ids[0].body

        self.assertTrue(task.name in last_message, 'Marking the task as done should be logged on the ticket.')

    def test_fsm_project(self):
        # Enable field service on the helpdesk team
        self.test_team.use_fsm = True
        # Find the first fsm project
        fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', self.test_team.company_id.id)], limit=1)
        # Default fsm_project should be the first fsm project with the oldest id
        self.assertEqual(self.test_team.fsm_project_id, fsm_project,
                         "The default fsm project should be from the same company.")

    def test_fsm_project_multicompany(self):
        extra_company = self.env['res.company'].create({'name': 'Extra Company'})
        fsm_project = self.env['project.project'].search([('is_fsm', '=', True), ('company_id', '=', extra_company.id)], limit=1)
        self.test_team.write({'company_id': extra_company.id})
        self.test_team.use_fsm = True
        self.assertEqual(self.test_team.fsm_project_id, fsm_project,
                         "The default fsm project should be from the same company.")

    def test_fsm_task_invited_user(self):
        invited_team = self.env['helpdesk.team'].create({
            'name': 'Test team invited internal',
            'use_fsm': True,
            'privacy_visibility': 'invited_internal'
        })

        ticket = self.env['helpdesk.ticket'].with_user(self.helpdesk_manager).create({
            'name': 'Ticket',
            'partner_id': self.partner.id,
            'team_id': invited_team.id,
            'user_id': self.helpdesk_user.id,
        })

        ticket_form = Form(ticket)
        ticket = ticket_form.save()

        action = ticket.with_user(self.helpdesk_user).action_generate_fsm_task()  # should not raise AccessError
        action_context = action['context']
        self.assertEqual(action_context['default_project_id'], ticket.team_id.fsm_project_id.id)
        self.assertEqual(action_context['default_helpdesk_ticket_id'], ticket.id)

    def test_generate_fsm_task_no_partner(self):
        self.test_team.use_fsm = True
        ticket = self.env['helpdesk.ticket'].with_user(self.helpdesk_manager).create({
            'name': 'Ticket',
            'team_id': self.test_team.id,
            'user_id': self.helpdesk_user.id,
        })
        action = ticket.action_generate_fsm_task()
        self.assertFalse(action['context']['default_partner_id'])

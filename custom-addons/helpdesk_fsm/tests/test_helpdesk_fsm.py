# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.helpdesk.tests.common import HelpdeskCommon
from odoo.tests.common import Form

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

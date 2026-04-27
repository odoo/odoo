# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

from freezegun import freeze_time


class HelpdeskSLA(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.test_team = cls.env['helpdesk.team'].create(
        {
            'name': 'Test Team SLA',
            'use_sla': True,
        })

        cls.stage_new, cls.stage_progress = cls.env['helpdesk.stage'].create([{
            'name': 'New',
            'sequence': 10,
            'team_ids': [cls.test_team.id],
        }, {
            'name': 'In Progress',
            'sequence': 20,
            'team_ids': [cls.test_team.id],
        }])

        cls.sla = cls.env['helpdesk.sla'].create({
            'name': 'SLA',
            'team_id': cls.test_team.id,
            'time': 32,
            'stage_id': cls.stage_progress.id,
            'priority': '1',
        })

    def create_ticket(self, team, *arg, **kwargs):
        default_values = {
            'name': "Help me",
            'team_id': team.id,
            'stage_id': self.stage_new.id,
            'priority': '1',
        }
        values = dict(default_values, **kwargs)
        return self.env['helpdesk.ticket'].create(values)

    def test_merge_ticket_sla(self):
        follower_1, follower_2 = self.env['res.partner'].create([
            {'name': 'Follower 1'},
            {'name': 'Follower 2'},
        ])

        with freeze_time('2024-09-03 15:00:00'):
            source_ticket = self.create_ticket(team=self.test_team, sla_ids=self.sla)
            source_ticket.message_subscribe([follower_1.id])
        with freeze_time('2024-09-02 15:00:00'):
            dest_ticket = self.create_ticket(team=self.test_team, sla_ids=self.sla)
            dest_ticket.message_subscribe([follower_1.id, follower_2.id])

        nearest_deadline = min(source_ticket.sla_status_ids.deadline, dest_ticket.sla_status_ids.deadline)
        self.env['helpdesk.ticket']._merge_method(dest_ticket, source_ticket)

        self.assertEqual(len(dest_ticket.message_follower_ids), 2, 'Follower 2 should be added')
        self.assertEqual(len(dest_ticket.sla_ids), 1, 'Same SLA policy should not be duplicated')
        self.assertEqual(len(dest_ticket.sla_status_ids), 1, 'Only one SLA should be kept')
        self.assertEqual(dest_ticket.sla_status_ids.deadline, nearest_deadline, 'Only the SLA with the nearest deadline should be kept')

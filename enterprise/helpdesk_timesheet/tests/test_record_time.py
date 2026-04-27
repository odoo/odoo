# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import HttpCase, tagged


@tagged('-at_install', 'post_install')
class TestRecordTimeHelpdesk(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.helpdesk_team_id = cls.env['helpdesk.team'].create({
            'name': 'Test Project Helpdesk Team',
            'use_helpdesk_timesheet': True,
        })
        cls.project_id = cls.helpdesk_team_id.project_id

    def test_record_time_new_helpdesk_ticket(self):
        self.start_tour('/web', 'timesheet_record_time_new_helpdesk_ticket', login='admin')

import json

from odoo.addons.account.tests.test_account_journal_dashboard_common import TestAccountJournalDashboardCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountJournalDashboardMailActivity(TestAccountJournalDashboardCommon):

    def test_journal_dashboard_activities(self):
        """ Test that activities on a journal and on its moves are correctly computed for the journal's dashboard. """
        journal = self.company_data['default_journal_misc']
        journal.activity_ids.unlink()

        activity_type_todo = self.env.ref('mail.mail_activity_data_todo')
        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'date': '2019-01-01',
            'line_ids': [
                (0, 0, {
                    'name': 'line_debit',
                    'account_id': self.company_data['default_account_revenue'].id,
                }),
            ]
        })

        activity_move = move.activity_schedule(
            activity_type_id=activity_type_todo.id,
            summary='Test Activity Move',
        )

        activity_journal = journal.activity_schedule(
            activity_type_id=activity_type_todo.id,
            summary='Test Activity Journal',
        )

        # Fetch activities on the dashboard
        journal_dashboard_activities = json.loads(journal.json_activity_data)['activities']
        self.assertEqual(len(journal_dashboard_activities), 2)
        self.assertEqual({act['id'] for act in journal_dashboard_activities}, {activity_move.id, activity_journal.id})

        # Mark move activity as done and archive journal activity
        activity_move.action_done()
        activity_journal.action_archive()
        self.env.flush_all()

        journal.invalidate_recordset(['json_activity_data'])
        journal_dashboard_activities = json.loads(journal.json_activity_data)['activities']
        self.assertEqual(len(journal_dashboard_activities), 0)

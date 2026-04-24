# # -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from dateutil.relativedelta import relativedelta

from odoo.fields import Date

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install', 'data_recycle')
class TestDataRecycle(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.server_model = cls.env['ir.model']._get('fetchmail.server')

        cls.recycle_model = cls.env['data_recycle.model'].create({
            'name': 'Recycle Test Server',
            'res_model_id': cls.server_model.id,
            'time_field_id': cls.env['ir.model.fields'].search([('name', '=', 'date'), ('model_id', '=', cls.server_model.id)], limit=1).id,
            'time_field_delta': 1,
            'time_field_delta_unit': 'years',
            'recycle_action': 'archive',
        })

        cls.old_servers = cls.env['fetchmail.server'].create([{
            'name': 'Old Server %s' % (i),
            'date': Date.today() - relativedelta(years=2),
        } for i in range(5)])

        cls.new_servers = cls.env['fetchmail.server'].create([{
            'name': 'New Server %s' % (i),
            'date': Date.today(),
        } for i in range(5)])

    def test_recycle_flow(self):
        # Test candidate search
        self.recycle_model._recycle_records()

        self.assertEqual(len(self.recycle_model.recycle_record_ids), 5)
        self.assertEqual(set(self.recycle_model.recycle_record_ids.mapped('res_id')), set(self.old_servers.ids))

        # Test record deletion outside of the recycle scope
        self.old_servers[0].unlink()
        self.assertEqual(self.recycle_model.recycle_record_ids[0].name, '**Record Deleted**')

    def test_recycle_domain(self):
        self.recycle_model.domain = "[('name', 'not ilike', '0')]"
        self.recycle_model._recycle_records()

        self.assertEqual(len(self.recycle_model.recycle_record_ids), 4)
        self.assertTrue(self.old_servers[0].id not in self.recycle_model.recycle_record_ids.mapped('res_id'))

    def test_recycle_notification(self):
        self.env.ref('base.user_admin').write({
            'email': 'mitchell.admin@example.com',
        })
        self.recycle_model.notify_user_ids = [(4, self.env.ref('base.user_admin').id)]
        old_notif_count = self.env['mail.notification'].search_count([])
        self.recycle_model._cron_recycle_records()
        new_notif_count = self.env['mail.notification'].search_count([])
        self.assertEqual(new_notif_count, old_notif_count + 1)

    def test_recycle_archive(self):
        self.recycle_model._recycle_records()
        self.recycle_model.recycle_record_ids.action_validate()
        self.assertFalse(self.recycle_model.recycle_record_ids.exists())
        self.assertTrue(all(not p.active for p in self.old_servers))

    def test_recycle_unlink(self):
        self.recycle_model.recycle_action = 'unlink'
        self.recycle_model._recycle_records()
        self.recycle_model.recycle_record_ids.action_validate()
        self.assertFalse(self.recycle_model.recycle_record_ids.exists())
        self.assertFalse(self.old_servers.exists())

    def test_include_archived(self):
        self.old_servers[0].active = False
        self.recycle_model._recycle_records()
        self.assertEqual(len(self.recycle_model.recycle_record_ids), 4)
        self.recycle_model.include_archived = True
        self.recycle_model._recycle_records()
        self.assertEqual(len(self.recycle_model.recycle_record_ids), 5)

    def test_time_field_defaults(self):
        """ Ensure that when no time field is specified, write_date with a 1-month delta is used by default. """
        recycle_model = self.env['data_recycle.model'].create({
            'name': 'Recycle Default Time Field',
            'res_model_id': self.server_model.id,
            'recycle_action': 'archive',
        })
        self.assertEqual(recycle_model.time_field_id.name, 'write_date', 'time_field_id should default to write_date.')
        self.assertEqual(recycle_model.time_field_delta, 1, 'time_field_delta should default to 1.')
        self.assertEqual(recycle_model.time_field_delta_unit, 'months', 'time_field_delta_unit should default to months.')

        # Only servers with write_date older than 1 month should be picked up.
        recycle_model._recycle_records()
        self.assertTrue(
            all(r.res_id in self.old_servers.ids for r in recycle_model.recycle_record_ids),
            'Only old servers should be queued for recycling.'
        )
        self.assertTrue(
            all(s.id not in recycle_model.recycle_record_ids.mapped('res_id') for s in self.new_servers),
            'New servers should not be queued for recycling.'
        )

    def test_time_field_user_override(self):
        """ Ensure that user-specified time_field_id and delta are preserved and applied correctly. """
        date_field = self.env['ir.model.fields'].search(
            [('name', '=', 'date'), ('model_id', '=', self.server_model.id)], limit=1)
        recycle_model = self.env['data_recycle.model'].create({
            'name': 'Recycle User Override Time Field',
            'res_model_id': self.server_model.id,
            'time_field_id': date_field.id,
            'time_field_delta': 6,
            'time_field_delta_unit': 'months',
            'recycle_action': 'archive',
        })
        self.assertEqual(
            recycle_model.time_field_id, date_field,
            'The time_field_id inputted by the user should not be overridden by the compute.'
        )

        # Servers with date older than 6 months are picked up, but not the ones created today.
        recycle_model._recycle_records()
        self.assertEqual(
            set(recycle_model.recycle_record_ids.mapped('res_id')), set(self.old_servers.ids),
            'Only the 2-year-old servers should be queued using the user-defined date field and 6-month delta.'
        )
        self.assertFalse(
            any(s.id in recycle_model.recycle_record_ids.mapped('res_id') for s in self.new_servers),
            'Servers created today should not be queued for recycling.'
        )

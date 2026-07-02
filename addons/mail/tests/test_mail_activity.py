from freezegun import freeze_time

from odoo import exceptions
from odoo.addons.mail.models import mail_activity as mail_activity_module
from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.tests import tagged, HttpCase

from unittest.mock import patch


@tagged("mail_activity")
class TestMailActivityChatter(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.test_partner = cls.env['res.partner'].create({
            'email': 'test.partner@example.com',
            'name': 'Test User',
        })

    def test_mail_activity_date_format(self):
        with freeze_time("2024-01-01 09:00:00 AM"):
            LANG_CODE = "en_US"
            self.env = self.env(context={"lang": LANG_CODE})
            lang = self.env["res.lang"].search([('code', '=', LANG_CODE)])
            lang.date_format = "%d/%b/%y"
            lang.time_format = "%I:%M:%S %p"

            self.start_tour(
                f"/web#id={self.test_partner.id}&model=res.partner",
                "mail_activity_date_format",
                login="admin",
            )

    def test_mail_activity_schedule_from_chatter(self):
        self.start_tour(
            f"/odoo/res.partner/{self.test_partner.id}",
            "mail_activity_schedule_from_chatter",
            login="admin",
        )


@tagged("mail_activity")
class TestMailActivityIntegrity(ActivityScheduleCase):

    def test_mail_activity_type_master_data(self):
        """ Test master data integrity

          * 'call', 'meeting', 'todo', 'upload document' and 'warning' should always be cross model;
          * 'call', 'meeting' and 'todo' cannot be removed
        """
        call = self.env.ref('mail.mail_activity_data_call')
        meeting = self.env.ref('mail.mail_activity_data_meeting')
        todo = self.env.ref('mail.mail_activity_data_todo')
        upload = self.env.ref('mail.mail_activity_data_upload_document')
        warning = self.env.ref('mail.mail_activity_data_warning')
        with self.assertRaises(exceptions.UserError):
            call.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            meeting.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            todo.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            upload.write({'res_model': 'res.partner'})
        with self.assertRaises(exceptions.UserError):
            warning.write({'res_model': 'res.partner'})

        with self.assertRaises(exceptions.UserError):
            call.unlink()
        with self.assertRaises(exceptions.UserError):
            meeting.unlink()
        with self.assertRaises(exceptions.UserError):
            todo.unlink()

    def test_mail_activity_read_access_search_with_limit(self):
        record = self.user_employee.partner_id.with_user(self.user_employee)
        ids = [record.activity_schedule(summary="test").id for _ in range(15)]
        activity_model = self.env['ir.model']._get("mail.activity")
        self.env['ir.rule'].create({
            'name': "No one allowed to view the created partner",
            'model_id': activity_model.id,
            'domain_force': [('id', 'not in', ids[5:10])],
        })
        self.env.transaction.invalidate_access_cache()

        activities = (self.env["mail.activity"]
            .with_user(self.user_employee)
        ).browse(ids)
        accessible = activities._filtered_access('read')
        self.assertEqual(len(accessible), 10)
        domain = ['|', ('id', 'in', ids), ('id', '<', 0)]  # added dummy constraint do avoid ids optimization

        self.assertEqual(activities.search(domain, limit=100), accessible)
        self.assertEqual(activities.sudo().search(domain, limit=100), activities)

        Activity = self.registry[activities._name]
        with (
            patch.object(mail_activity_module, 'PREFETCH_MAX', 3),
            patch.object(Activity, '_search', autospec=True, side_effect=Activity._search) as search_func,
        ):
            self.assertEqual(activities.search(domain, limit=100), accessible)
            self.assertGreaterEqual(search_func.call_count, 4)

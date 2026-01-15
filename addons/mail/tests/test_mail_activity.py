from freezegun import freeze_time

from odoo import exceptions
from odoo.addons.mail.tests.common_activity import ActivityScheduleCase
from odoo.tests import tagged, HttpCase


@tagged("mail_activity", "-at_install", "post_install")
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


@tagged("-at_install", "post_install", "mail_activity")
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

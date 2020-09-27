from odoo.tests import TransactionCase


class TestMailAccess(TransactionCase):
    def setUp(self):
        super().setUp()
        self.user_admin = self.env.ref('base.user_admin')
        self.user_demo = self.env.ref('base.user_demo')
        self.partner = self.env.ref('base.res_partner_2')

    def test_send_mail_on_activity(self):
        """Send an e-mail related to the activity model

        According to record rules, write access is granted to the activity model only if that activity
        is assigned to the current user.

        when an email is sent related to a model, write access is checked in that model,
         which shouldn't fail if the activity is not assigned to the current user.
        """
        # Register an activity on a partner, assigned to a different user
        self.uid = self.user_admin
        activity = self.partner.activity_schedule(
            'mail.mail_activity_data_todo',
            note='Pending activity on customer',
            user_id=self.user_demo.id
        )

        # Send an email related to the created activity
        mail_template = self.env['mail.template'].create({
            'name': 'Mail Activity Created',
            'model_id': self.env.ref('mail.model_mail_activity').id,
            'email_to': "${object.user_id.email or '' | safe}",
        })
        mail_template.send_mail(activity.id)

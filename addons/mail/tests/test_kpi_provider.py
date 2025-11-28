from odoo.tests import new_test_user, tagged, TransactionCase, users


@tagged('post_install', '-at_install')
class TestKpiProvider(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.user_someemployee = new_test_user(cls.env, name='Some Employee', login='someemployee')
        cls.user_anotheremployee = new_test_user(cls.env, name='AnotherEmployee', login='anotheremployee')

        cls.env['mail.activity'].create([{
            'activity_type_id': cls.env.ref('mail.mail_activity_data_todo').id,
            'user_id': cls.user_someemployee.id,
        }, {
            'activity_type_id': cls.env.ref('mail.mail_activity_data_meeting').id,
            'user_id': cls.user_someemployee.id,
        }, {
            'activity_type_id': cls.env.ref('mail.mail_activity_data_meeting').id,
            'user_id': cls.user_anotheremployee.id,
        }])

    @users('someemployee')
    def test_kpi_summary(self):
        """ Ensure that a user will see their own mail activities if their visibility is 'own' """

        self.assertCountEqual(self.env['kpi.provider'].get_mail_activities_kpi_summary(), [
            {'id': 'mail_activity_type.mail_mail_activity_data_todo', 'name': 'To-Do', 'type': 'integer', 'value': 1},
            {'id': 'mail_activity_type.mail_mail_activity_data_meeting', 'name': 'Meeting', 'type': 'integer', 'value': 1},
        ])

    @users('someemployee')
    def test_kpi_summary_visibility_all(self):
        """ Ensure that a user will see two meetings if the visibility is 'all' """

        self.env.ref('mail.mail_activity_data_meeting').sudo().kpi_provider_visibility = 'all'

        self.assertCountEqual(self.env['kpi.provider'].get_mail_activities_kpi_summary(), [
            {'id': 'mail_activity_type.mail_mail_activity_data_todo', 'name': 'To-Do', 'type': 'integer', 'value': 1},
            {'id': 'mail_activity_type.mail_mail_activity_data_meeting', 'name': 'Meeting', 'type': 'integer', 'value': 2},
        ])

    @users('someemployee')
    def test_kpi_summary_visibility_none(self):
        """ Ensure that a user won't see any meetings if the visibility is 'none' """

        self.env.ref('mail.mail_activity_data_meeting').sudo().kpi_provider_visibility = 'none'

        self.assertCountEqual(self.env['kpi.provider'].get_mail_activities_kpi_summary(), [
            {'id': 'mail_activity_type.mail_mail_activity_data_todo', 'name': 'To-Do', 'type': 'integer', 'value': 1},
        ])

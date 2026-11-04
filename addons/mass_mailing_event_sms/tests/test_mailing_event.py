from ast import literal_eval

from odoo.addons.event.tests.common import EventCase
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.tests.common import users
from odoo.tests import tagged, Form


@tagged('post_install', '-at_install')
class TestMassMailEventValues(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.manager_event_marketing = mail_new_test_user(
            cls.env,
            groups='base.group_user,base.group_partner_manager,mass_mailing.group_mass_mailing_user,event.group_event_manager',
            login='manager_event_marketing',
            name='Event Marketing',
            signature='--\nTest User',
        )

    @users('manager_event_marketing')
    def test_mailing_event_computed_fields_form(self):
        test_event = self.env['event.event'].create({
            'name': 'Test Default Event',
        })
        self.env['event.registration'].with_user(self.user_eventuser).create({
            'name': 'TestReg1',
            'event_id': test_event.id,
        })

        mailing_form = Form(self.env['mailing.mailing'].with_context(
            default_mailing_model_id=self.env['ir.model']._get('event.registration').id,
            default_mailing_domain=f"[('event_id', 'in', {test_event.ids}), ('state', 'not in', ['cancel', 'draft'])]",
        ), view='mass_mailing_sms.mailing_mailing_view_form_mixed')
        mailing_form.mailing_type = 'sms'
        self.assertEqual(
            literal_eval(mailing_form.mailing_domain),
            [('event_id', 'in', test_event.ids), ('state', 'not in', ['cancel', 'draft'])],
        )

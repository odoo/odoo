import socket

from email.utils import formataddr

from odoo.addons.test_mail.data.test_mail_data import \
    MAIL_TEMPLATE, MAIL_TEMPLATE_PLAINTEXT, MAIL_MULTIPART_MIXED, MAIL_MULTIPART_MIXED_TWO, \
    MAIL_MULTIPART_IMAGE, MAIL_SINGLE_BINARY

from odoo.addons.test_mail.tests.common import BaseFunctionalTest, MockEmails

from odoo.addons.test_mail.models.test_mail_models import MailTestPartner
from odoo.addons.mail.models.mail_partner import MailPartnerMixin

from odoo.tools import mute_logger
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

class TestMailPartner(BaseFunctionalTest, MockEmails):

    @classmethod
    def setUpClass(cls):
        super(TestMailPartner, cls).setUpClass()
        mail_test_model = cls.env['ir.model']._get('mail.partner.test')

        # partnercreatetest@.. will cause the creation of new mail.partner.test
        cls.alias = cls.env['mail.alias'].create({
            'alias_name': 'partnercreatetest',
            'alias_user_id': False,
            'alias_model_id': mail_test_model.id,
            'alias_contact': 'everyone'})


    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.models')
    def test_onreply_workflow(self):

        with patch.object(MailTestPartner, '_message_partner_update_condition', return_value=[('value', '!=', 5), ('value2', '=', 7)]):
            emailfrom = 'testonreply@example.com'
            msgid = '<123456.testonreply@example.com>'
            #maybe test wit formataddr(('name', 'testoncreate@example.com'))
            record = self.format_and_process(
                MAIL_TEMPLATE,
                subject='Specific',
                to='partnercreatetest@example.com',
                target_model='mail.partner.test',
                email_from=emailfrom,
                msg_id=msgid
                )
            #set fields so that the partner_id can be updated
            record.value = 4
            record.value2 = 7
            # Test: one group created by mailgateway administrator as user_id is not set
            self.assertEqual(len(record), 1, 'message_process: a new mail.partner.test should have been created')
            #the email_from, name, email_cc should be correctly setted
            self.assertEqual(emailfrom, record.email_from, 'email_from should have been correctly setted')
            self.assertEqual("", record.email_cc, 'email_cc should have been correctly setted')
            self.assertEqual("Specific", record.name, 'email_from should have been correctly setted')

            #after creation, no follower should have been added
            self.assertEqual(0, len(record.message_follower_ids), 'A follower shouldn\'t have been added automaticaly')

            #region create_records
            #create some records manually to check the update later
            partner_1 = self.env['res.partner'].with_context(self._quick_create_ctx).create({
                'name': 'Valid Lelitre',
                'email': 'valid.lelitre@agrolait.com',
            })
            b_record_1 = self.env['mail.partner.test'].create({
                        'email_from': emailfrom,
                        'partner_id': partner_1.id,
                        'value': 4,
                        'value2': 7
                    })
            b_record_2 = self.env['mail.partner.test'].create({
                        'email_from': "another@email.com",
                        'value': 4,
                        'value2': 7
                    })
            b_record_3 = self.env['mail.partner.test'].create({
                        'email_from': emailfrom,
                        'value': 5,
                        'value2': 7
                    })
                    
            b_record_4 = self.env['mail.partner.test'].create({
                        'email_from': emailfrom,
                        'value': 4,
                        'value2': 5
                    })
            
            c_record_1 = self.env['mail.partner.test'].create({
                        'email_from': emailfrom,
                        'value': 4,
                        'value2': 7
                    })

            c_record_2 = self.env['mail.partner.test'].create({
                        'email_from': emailfrom,
                        'value': 9,
                        'value2': 7
                    })
            #endregion
            #send a repply mail from the same email that shouldn't trigger partner creation
            self.format_and_process(
                MAIL_TEMPLATE,
                subject='Re: Specific',
                to='partnercreatetest@example.com',
                target_model='mail.partner.test',
                email_from=emailfrom,
                extra='In-Reply-To:\r\n\t%s\n' % msgid
                )

            self.assertEqual(0, len(record.message_follower_ids), 'A follower shouldn\'t have been added automaticaly since the email is not linked to a user')

            #send a repply mail from demo that should trigger partner creation
            self.format_and_process(
                MAIL_TEMPLATE,
                subject='Re: Specific',
                to='partnercreatetest@example.com',
                target_model='mail.partner.test',
                email_from=self.env.ref('base.user_demo').email,
                extra='In-Reply-To:\r\n\t%s\n' % msgid,
                msg_id='1234%s' % self.env.ref('base.user_demo').email
                )

            #note: this test also prove that with the current implementation a user can subscibe himself to a topic by 
            # sending a mail in repply to his own email. This could be an issue
            #we should have one follower corresponding to a new partner with the email_from email address
            self.assertEqual(1, len(record.message_follower_ids), 'A follower should have been added automaticaly')
            self.assertEqual(emailfrom, record.message_follower_ids[0].partner_id.email, 'The follower should have the correct email adress')
            self.assertEqual(record.partner_id, record.message_follower_ids[0].partner_id, 'The partner should have been linked to the record')

            #check other records: basic condition
            self.assertEqual(b_record_1.partner_id.id, partner_1.id, 'The partner should not have been updated if already set')
            self.assertEqual(len(b_record_2.partner_id), 0, 'The partner should not have been updated if the email is not matching')
            #check other records: aditionnal condition is [('value', '!=', 5),('value2', '=', 7)]
            self.assertEqual(len(b_record_3.partner_id), 0, 'The partner should not have been updated if one condition does not match')
            self.assertEqual(len(b_record_4.partner_id), 0, 'The partner should not have been updated if one condition does not match')
            #check other records, some should have been updated
            self.assertEqual(c_record_1.partner_id.id, record.partner_id.id, 'The partner should not have been updated if all condition match')
            self.assertEqual(c_record_2.partner_id.id, record.partner_id.id, 'The partner should not have been updated if all condition match')

    def test_oncreate_workflow(self):
        with patch.object(MailTestPartner, '_partner_creation_strategy', return_value=MailPartnerMixin.ALWAYS_STRATEGY):
            emailfrom = 'testoncreate@example.com'
            msgid = '<123456.testoncreatey@example.com>'
            #maybe add test wit formataddr(('name', 'testoncreate@example.com'))
            record = self.format_and_process(
                MAIL_TEMPLATE,
                subject='Specific OnCreate',
                to='partnercreatetest@example.com',
                target_model='mail.partner.test',
                email_from=emailfrom,
                msg_id=msgid
                )
            
            # Test: one group created by mailgateway administrator as user_id is not set
            self.assertEqual(len(record), 1, 'message_process: a new mail.partner.test should have been created')
            #the email_from, name, email_cc should be correctly setted
            self.assertEqual(emailfrom, record.email_from, 'email_from should have been correctly setted')
            self.assertEqual("", record.email_cc, 'email_cc should have been correctly setted')
            self.assertEqual("Specific OnCreate", record.name, 'subject should have been correctly setted')
            #we should have one follower corresponding to a new partner with the email_from email address
            self.assertEqual(1, len(record.message_follower_ids), 'A follower should have been added automaticaly')
            self.assertEqual(emailfrom, record.message_follower_ids[0].partner_id.email, 'The follower should have the correct email adress')
            self.assertEqual(record.partner_id.id, record.message_follower_ids[0].partner_id.id, 'The partner should have been linked to the record')

    def test_cc_subscription_always_default(self):
        with patch.object(MailTestPartner, '_partner_creation_strategy', return_value=MailPartnerMixin.ALWAYS_STRATEGY):
            emailfrom = 'testoncreate@example.com'
            msgid = '<123456.testoncreatey@example.com>'
            demo_user_email = self.env.ref('base.user_demo').email
            #maybe add test wit formataddr(('name', 'testoncreate@example.com'))
            record = self.format_and_process(
                MAIL_TEMPLATE,
                subject='Specific OnCreate',
                to='partnercreatetest@example.com',
                target_model='mail.partner.test',
                email_from=emailfrom,
                cc='%s; unknowemail@example.com' % demo_user_email,
                msg_id=msgid
                )
            self.assertEqual(2, len(record.message_follower_ids), 'Two follower should have been added automaticaly')
            self.assertEqual([emailfrom, demo_user_email], [x.partner_id.email for x in record.message_follower_ids], 'The followers should have the correct email adress')

    def test_cc_subscription_always_nocc(self):
        with patch.object(MailTestPartner, '_partner_creation_strategy', return_value=MailPartnerMixin.ALWAYS_STRATEGY):
            with patch.object(MailTestPartner, '_emails_subscribe_if_exists', return_value=[]):
                emailfrom = 'testoncreate@example.com'
                msgid = '<123456.testoncreatey@example.com>'
                demo_user_email = self.env.ref('base.user_demo').email
                #maybe add test wit formataddr(('name', 'testoncreate@example.com'))
                record = self.format_and_process(
                    MAIL_TEMPLATE,
                    subject='Specific OnCreate',
                    to='partnercreatetest@example.com',
                    target_model='mail.partner.test',
                    email_from=emailfrom,
                    cc='%s; unknowemail@example.com' % demo_user_email,
                    msg_id=msgid
                    )
                self.assertEqual(1, len(record.message_follower_ids), 'One follower should have been added automaticaly')
                self.assertEqual([emailfrom], [x.partner_id.email for x in record.message_follower_ids], 'The followers should have the correct email adress')

    def test_cc_subscription_default_nocc(self):
        with patch.object(MailTestPartner, '_emails_subscribe_if_exists', return_value=[]):
            emailfrom = 'testoncreate@example.com'
            msgid = '<123456.testoncreatey@example.com>'
            demo_user_email = self.env.ref('base.user_demo').email
            #maybe add test wit formataddr(('name', 'testoncreate@example.com'))
            record = self.format_and_process(
                MAIL_TEMPLATE,
                subject='Specific OnCreate',
                to='partnercreatetest@example.com',
                target_model='mail.partner.test',
                email_from=emailfrom,
                cc='%s; unknowemail@example.com' % demo_user_email,
                msg_id=msgid
                )
            self.assertEqual(0, len(record.message_follower_ids), 'No follower should have been added automaticaly')

    def test_cc_subscription_default_default_with_answer(self):
        emailfrom = 'testoncreate@example.com'
        msgid = '<123456.testoncreatey@example.com>'
        demo_user_email = self.env.ref('base.user_demo').email
        admin_user_email = self.env.ref('base.user_root').email
        #maybe add test wit formataddr(('name', 'testoncreate@example.com'))
        record = self.format_and_process(
            MAIL_TEMPLATE,
            subject='Specific OnCreate',
            to='partnercreatetest@example.com',
            target_model='mail.partner.test',
            email_from=emailfrom,
            cc='%s; unknowemail@example.com' % demo_user_email,
            msg_id=msgid
            )
        self.assertEqual(1, len(record.message_follower_ids), 'One follower should have been added automaticaly')
        self.assertEqual([demo_user_email], [x.partner_id.email for x in record.message_follower_ids], 'The followers should have the correct email adress')

        self.format_and_process(
            MAIL_TEMPLATE,
            subject='Re: Specific',
            to='partnercreatetest@example.com',
            target_model='mail.partner.test',
            email_from=demo_user_email,
            extra='In-Reply-To:\r\n\t%s\n' % msgid,
            cc=" %s" % admin_user_email,
            msg_id='1234%s' % self.env.ref('base.user_demo').email
            )
        self.assertEqual(3, len(record.message_follower_ids), 'Three follower should have been added automaticaly')
        self.assertEqual([demo_user_email, emailfrom, admin_user_email], [x.partner_id.email for x in record.message_follower_ids], 'The followers should have the correct email adress')

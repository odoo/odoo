# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common
from odoo.tests.common import users


class TestSMSComposerComment(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.MockEmails, test_mail_common.TestRecipients):
    """ TODO LIST

     * add test for default_res_model / default_res_id and stuff like that
     * add test for comment put in queue
    """

    @classmethod
    def setUpClass(cls):
        super(TestSMSComposerComment, cls).setUpClass()
        cls._test_body = 'VOID CONTENT'

        cls.partner_numbers = [
            phone_validation.phone_format(partner.mobile, partner.country_id.code, partner.country_id.phone_code, force_format='E164')
            for partner in (cls.partner_1 | cls.partner_2)
        ]

        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
            'mobile_nbr': cls.test_numbers[0],
            'phone_nbr': cls.test_numbers[1],
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)

        cls.sms_template = cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': cls.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear ${object.display_name} this is an SMS.',
        })

    def test_composer_comment_not_mail_thread(self):
        with self.sudo('employee'):
            record = self.env['test_performance.base'].create({'name': 'TestBase'})
            composer = self.env['sms.composer'].with_context(
                active_model='test_performance.base', active_id=record.id
            ).create({
                'body': self._test_body,
                'numbers': ','.join(self.random_numbers),
            })

            with self.mockSMSGateway():
                composer._action_send_sms()

        self.assertSMSSent(self.random_numbers_san, self._test_body)

    def test_composer_comment_default(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                active_model='mail.test.sms', active_id=self.test_record.id
            ).create({
                'body': self._test_body,
            })

            with self.mockSMSGateway():
                messages = composer._action_send_sms()

        self.assertSMSNotification([{'partner': self.test_record.customer_id, 'number': self.test_numbers_san[1]}], self._test_body, messages)

    def test_composer_comment_field_1(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                active_model='mail.test.sms', active_id=self.test_record.id,
            ).create({
                'body': self._test_body,
                'number_field_name': 'mobile_nbr',
            })

            with self.mockSMSGateway():
                messages = composer._action_send_sms()

        self.assertSMSNotification([{'partner': self.test_record.customer_id, 'number': self.test_numbers_san[0]}], self._test_body, messages)

    def test_composer_comment_field_2(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                active_model='mail.test.sms', active_id=self.test_record.id,
            ).create({
                'body': self._test_body,
                'number_field_name': 'phone_nbr',
            })

            with self.mockSMSGateway():
                messages = composer._action_send_sms()

        self.assertSMSNotification([{'partner': self.test_record.customer_id, 'number': self.test_numbers_san[1]}], self._test_body, messages)

        # TDE FIXME THIS IS SHIT IN POOP
        # partners = self.partner_1 | self.partner_2 | partner_incorrect

        # composer = self.env['sms.composer'].with_context(
        #     active_model='res.partner',
        #     active_domain=[('id', 'in', partners.ids)]
        # ).create({
        #     'message': self._test_body,
        # })

        # with self.mockSMSGateway():
        #     composer.action_send_sms()
        # self.assertSMSSent((self.partner_1 | self.partner_2).mapped('mobile'), test_body)  # TDE FIXME: actually sanitizer does not work in current master (saas 12.23))

    def test_composer_comment_field_w_numbers(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                active_model='mail.test.sms', active_id=self.test_record.id,
                default_number_field_name='mobile_nbr',
            ).create({
                'body': self._test_body,
                'numbers': ','.join(self.random_numbers),
            })

            with self.mockSMSGateway():
                messages = composer._action_send_sms()

        self.assertSMSNotification([
            {'partner': self.test_record.customer_id, 'number': self.test_record.mobile_nbr},
            {'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}], self._test_body, messages)

    def test_composer_comment_field_w_template(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                active_model='mail.test.sms', active_id=self.test_record.id,
                default_template_id=self.sms_template.id,
                default_number_field_name='mobile_nbr',
            ).create({})

            with self.mockSMSGateway():
                messages = composer._action_send_sms()

        self.assertSMSNotification([{'partner': self.test_record.customer_id, 'number': self.test_record.mobile_nbr}], 'Dear %s this is an SMS.' % self.test_record.display_name, messages)

    def test_composer_numbers_no_model(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                default_composition_mode='numbers'
            ).create({
                'body': self._test_body,
                'numbers': ','.join(self.random_numbers),
            })

            with self.mockSMSGateway():
                composer._action_send_sms()
        self.assertSMSSent(self.random_numbers_san, self._test_body)

    # def test_composer_partners_sanitize(self):
    #     partner_incorrect = self.env['res.partner'].create({
    #         'name': 'Jean-Claude Incorrect',
    #         'email': 'jean.claude@example.com',
    #         'mobile': 'coincoin',
    #         })
    #     partners = self.partner_1 | self.partner_2 | partner_incorrect
    #     composer = self.env['sms.composer'].with_context(
    #         active_model='res.partner',
    #         active_domain=[('id', 'in', partners.ids)]
    #     ).create({
    #         'body': self._test_body,
    #     })

    #     with self.mockSMSGateway():
    #         composer.action_send_sms()
        # self.assertSMSSent((self.partner_1 | self.partner_2).mapped('mobile'), test_body)  # TDE FIXME: actually sanitizer does not work in current master (saas 12.23))


class TestSMSComposerMass(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.MockEmails, test_mail_common.TestRecipients):
    """ TODO LIST

    * add test for mass with log note
    """

    @classmethod
    def setUpClass(cls):
        super(TestSMSComposerMass, cls).setUpClass()
        cls._test_body = 'Zizisse an SMS.'

        records = cls.env['mail.test.sms']
        partners = cls.env['res.partner']
        country_id = cls.env.ref('base.be').id,
        for x in range(3):
            partners += cls.env['res.partner'].with_context(**cls._test_context).create({
                'name': 'Partner_%s' % (x),
                'email': '_test_partner_%s@example.com' % (x),
                'country_id': country_id,
                'mobile': '047500%s%s99' % (x, x)
            })
            records += cls.env['mail.test.sms'].with_context(**cls._test_context).create({
                'name': 'Test_%s' % (x),
                'customer_id': partners[x].id,
            })
        cls.records = cls._reset_mail_context(records)
        cls.partners = partners

        cls.sms_template = cls.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': cls.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear ${object.display_name} this is an SMS.',
        })

    def test_composer_mass_active_domain(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                default_composition_mode='mass',
                default_res_model='mail.test.sms',
                default_use_active_domain=True,
                active_domain=repr([('id', 'in', self.records.ids)]),
            ).create({
                'body': self._test_body,
            })

            with self.mockSMSGateway():
                composer.action_send_sms()

        for record in self.records:
            self.assertSMSOutgoing(record.customer_id, None, self._test_body)

    def test_composer_mass_active_domain_w_template(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                default_composition_mode='mass',
                default_res_model='mail.test.sms',
                default_use_active_domain=True,
                active_domain=repr([('id', 'in', self.records.ids)]),
                default_template_id=self.sms_template.id,
            ).create({
            })

            with self.mockSMSGateway():
                composer.action_send_sms()

        for record in self.records:
            self.assertSMSOutgoing(record.customer_id, None, 'Dear %s this is an SMS.' % record.display_name)

    def test_composer_mass_active_ids(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                default_composition_mode='mass',
                default_res_model='mail.test.sms',
                active_ids=self.records.ids,
            ).create({
                'body': self._test_body,
            })

            with self.mockSMSGateway():
                composer.action_send_sms()

        for partner in self.partners:
            self.assertSMSOutgoing(partner, None, self._test_body)

    def test_composer_mass_active_ids_w_template(self):
        with self.sudo('employee'):
            composer = self.env['sms.composer'].with_context(
                default_composition_mode='mass',
                default_res_model='mail.test.sms',
                active_ids=self.records.ids,
                default_template_id=self.sms_template.id,
            ).create({})

            with self.mockSMSGateway():
                composer.action_send_sms()

        for record in self.records:
            self.assertSMSOutgoing(record.customer_id, None, 'Dear %s this is an SMS.' % record.display_name)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.sms.tests import common as sms_common
from odoo.addons.test_mail.tests import common as test_mail_common
from odoo.addons.test_mail_full.tests import common as test_mail_full_common


class TestSMSPost(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.MockEmails, test_mail_common.TestRecipients):
    """ TODO

      * add tests for new mail.message and mail.thread fields;
    """

    @classmethod
    def setUpClass(cls):
        super(TestSMSPost, cls).setUpClass()
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

    def test_message_sms_internals_body(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms('<p>Mega SMS<br/>Top moumoutte</p>', partner_ids=self.partner_1.ids)

        self.assertEqual(messages.body, '<p>Mega SMS<br>Top moumoutte</p>')
        self.assertEqual(messages.subtype_id, self.env.ref('mail.mt_note'))
        self.assertSMSNotification([{'partner': self.partner_1}], 'Mega SMS\nTop moumoutte', messages)

    def test_message_sms_internals_check_existing(self):
        with self.sudo('employee'), self.mockSMSGateway(sim_error='wrong_format_number'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.partner_1.ids)

        self.assertSMSNotification([{'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_number_format'}], self._test_body, messages)

        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            test_record._notify_record_by_sms(messages, {'partners': [{'id': self.partner_1.id, 'notif': 'sms'}]}, check_existing=True)
        self.assertSMSNotification([{'partner': self.partner_1}], self._test_body, messages)

    def test_message_sms_internals_sms_numbers(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.partner_1.ids, sms_numbers=self.random_numbers)

        self.assertSMSNotification([{'partner': self.partner_1}, {'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_internals_subtype(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms('<p>Mega SMS<br/>Top moumoutte</p>', subtype_id=self.env.ref('mail.mt_comment').id, partner_ids=self.partner_1.ids)

        self.assertEqual(messages.body, '<p>Mega SMS<br>Top moumoutte</p>')
        self.assertEqual(messages.subtype_id, self.env.ref('mail.mt_comment'))
        self.assertSMSNotification([{'partner': self.partner_1}], 'Mega SMS\nTop moumoutte', messages)

    def test_message_sms_internals_pid_to_number(self):
        pid_to_number = {
            self.partner_1.id: self.random_numbers[0],
            self.partner_2.id: self.random_numbers[1],
        }
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids, sms_pid_to_number=pid_to_number)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'number': self.random_numbers_san[0]},
            {'partner': self.partner_2, 'number': self.random_numbers_san[1]}],
            self._test_body, messages)

    def test_message_sms_model_partner(self):
        with self.sudo('employee'), self.mockSMSGateway():
            messages = self.partner_1._message_sms(self._test_body)
            messages |= self.partner_2._message_sms(self._test_body)
        self.assertSMSNotification([{'partner': self.partner_1}, {'partner': self.partner_2}], self._test_body, messages)

    def test_message_sms_model_partner_fallback(self):
        self.partner_1.write({'mobile': False, 'phone': self.random_numbers[0]})

        with self.mockSMSGateway():
            messages = self.partner_1._message_sms(self._test_body)
            messages |= self.partner_2._message_sms(self._test_body)

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.random_numbers_san[0]}, {'partner': self.partner_2}], self._test_body, messages)

    def test_message_sms_model_w_partner_only(self):
        with self.sudo('employee'):
            record = self.env['mail.test.sms.partner'].create({'partner_id': self.partner_1.id})

            with self.mockSMSGateway():
                messages = record._message_sms(self._test_body)

        self.assertSMSNotification([{'partner': self.partner_1}], self._test_body, messages)

    def test_message_sms_model_w_partner_only_void(self):
        with self.sudo('employee'):
            record = self.env['mail.test.sms.partner'].create({'partner_id': False})

            with self.mockSMSGateway():
                messages = record._message_sms(self._test_body)

        # should not crash but no sms / no recipients
        notifs = self.env['mail.notification'].search([('mail_message_id', 'in', messages.ids)])
        self.assertFalse(notifs)

    def test_message_sms_on_field_w_partner(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, number_field='mobile_nbr')

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_record.mobile_nbr}], self._test_body, messages)

    def test_message_sms_on_field_wo_partner(self):
        self.test_record.write({'customer_id': False})

        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, number_field='mobile_nbr')

        self.assertSMSNotification([{'number': self.test_record.mobile_nbr}], self._test_body, messages)

    def test_message_sms_on_field_wo_partner_default_field(self):
        self.test_record.write({'customer_id': False})

        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body)

        self.assertSMSNotification([{'number': self.test_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_field_wo_partner_default_field_2(self):
        self.test_record.write({'customer_id': False, 'phone_nbr': False})

        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body)

        self.assertSMSNotification([{'number': self.test_numbers_san[0]}], self._test_body, messages)

    def test_message_sms_on_numbers(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, sms_numbers=self.random_numbers_san)
        self.assertSMSNotification([{'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_numbers_sanitization(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, sms_numbers=self.random_numbers)
        self.assertSMSNotification([{'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_partner_ids(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids)

        self.assertSMSNotification([{'partner': self.partner_1}, {'partner': self.partner_2}], self._test_body, messages)

    def test_message_sms_on_partner_ids_default(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body)

        self.assertSMSNotification([{'partner': self.test_record.customer_id, 'number': self.test_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_partner_ids_w_numbers(self):
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.partner_1.ids, sms_numbers=self.random_numbers[:1])

        self.assertSMSNotification([{'partner': self.partner_1}, {'number': self.random_numbers_san[0]}], self._test_body, messages)

    def test_message_sms_with_template(self):
        sms_template = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear ${object.display_name} this is an SMS.',
        })

        with self.sudo('employee'):
            with self.mockSMSGateway():
                test_record = self.env['mail.test.sms'].browse(self.test_record.id)
                messages = test_record._message_sms_with_template(template=sms_template)

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_numbers_san[1]}], 'Dear %s this is an SMS.' % self.test_record.display_name, messages)

    def test_message_sms_with_template_fallback(self):
        with self.sudo('employee'):
            with self.mockSMSGateway():
                test_record = self.env['mail.test.sms'].browse(self.test_record.id)
                messages = test_record._message_sms_with_template(template_xmlid='test_mail_full.this_should_not_exists', template_fallback='Fallback for ${object.id}')

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_numbers_san[1]}], 'Fallback for %s' % self.test_record.id, messages)

    def test_message_sms_with_template_xmlid(self):
        sms_template = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear ${object.display_name} this is an SMS.',
        })
        self.env['ir.model.data'].create({
            'name': 'this_should_exists',
            'module': 'test_mail_full',
            'model': sms_template._name,
            'res_id': sms_template.id,
        })

        with self.sudo('employee'):
            with self.mockSMSGateway():
                test_record = self.env['mail.test.sms'].browse(self.test_record.id)
                messages = test_record._message_sms_with_template(template_xmlid='test_mail_full.this_should_exists')

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_numbers_san[1]}], 'Dear %s this is an SMS.' % self.test_record.display_name, messages)


class TestSMSPostException(test_mail_full_common.BaseFunctionalTest, sms_common.MockSMS, test_mail_common.MockEmails, test_mail_common.TestRecipients):

    @classmethod
    def setUpClass(cls):
        super(TestSMSPostException, cls).setUpClass()
        cls._test_body = 'VOID CONTENT'

        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)
        cls.partner_3 = cls.env['res.partner'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
            'no_reset_password': True,
        }).create({
            'name': 'Ernestine Loubine',
            'email': 'ernestine.loubine@agrolait.com',
            'country_id': cls.env.ref('base.be').id,
            'mobile': '0475556644',
        })

    def test_message_sms_w_numbers_invalid(self):
        random_numbers = self.random_numbers + ['6988754']
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, sms_numbers=random_numbers)

        # invalid numbers are still given to IAP currently as they are
        self.assertSMSNotification([{'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}, {'number': random_numbers[2]}], self._test_body, messages)

    def test_message_sms_w_partners_nocountry(self):
        self.test_record.customer_id.write({
            'mobile': self.random_numbers[0],
            'phone': self.random_numbers[1],
            'country_id': False,
        })
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.test_record.customer_id.ids)

        self.assertSMSNotification([{'partner': self.test_record.customer_id}], self._test_body, messages)

    def test_message_sms_w_partners_falsy(self):
        # TDE FIXME: currently sent to IAP
        self.test_record.customer_id.write({
            'mobile': 'youpie',
            'phone': 'youpla',
        })
        with self.sudo('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.test_record.customer_id.ids)

        # self.assertSMSNotification({self.test_record.customer_id: {}}, {}, self._test_body, messages)

    def test_message_sms_w_numbers_sanitization_duplicate(self):
        pass
        # TDE FIXME: not sure
        # random_numbers = self.random_numbers + [self.random_numbers[1]]
        # random_numbers_san = self.random_numbers_san + [self.random_numbers_san[1]]
        # with self.sudo('employee'), self.mockSMSGateway():
        #     messages = self.test_record._message_sms(self._test_body, sms_numbers=random_numbers)
        # self.assertSMSNotification({}, {random_numbers_san[0]: {}, random_numbers_san[1]: {}, random_numbers_san[2]: {}}, self._test_body, messages)

    def test_message_sms_crash_credit(self):
        with self.sudo('employee'), self.mockSMSGateway(sim_error='credit'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_credit'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_credit'},
        ], self._test_body, messages)

    def test_message_sms_crash_credit_single(self):
        with self.sudo('employee'), self.mockSMSGateway(nbr_t_error={phone_validation.phone_get_sanitized_record_number(self.partner_2): 'credit'}):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2 | self.partner_3).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'sent'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_credit'},
            {'partner': self.partner_3, 'state': 'sent'},
        ], self._test_body, messages)

    def test_message_sms_crash_server_crash(self):
        with self.sudo('employee'), self.mockSMSGateway(sim_error='jsonrpc_exception'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2 | self.partner_3).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_server'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_server'},
            {'partner': self.partner_3, 'state': 'exception', 'failure_type': 'sms_server'},
        ], self._test_body, messages)

    def test_message_sms_crash_wrong_number(self):
        with self.sudo('employee'), self.mockSMSGateway(sim_error='wrong_format_number'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_number_format'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_number_format'},
        ], self._test_body, messages)

    def test_message_sms_crash_wrong_number_single(self):
        with self.sudo('employee'), self.mockSMSGateway(nbr_t_error={phone_validation.phone_get_sanitized_record_number(self.partner_2): 'wrong_format_number'}):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2 | self.partner_3).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'sent'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_number_format'},
            {'partner': self.partner_3, 'state': 'sent'},
        ], self._test_body, messages)

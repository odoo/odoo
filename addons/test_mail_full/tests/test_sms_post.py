# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mail_full.tests.common import TestMailFullCommon, TestMailFullRecipients


class TestSMSPost(TestMailFullCommon, TestMailFullRecipients):
    """ TODO

      * add tests for new mail.message and mail.thread fields;
    """

    @classmethod
    def setUpClass(cls):
        super(TestSMSPost, cls).setUpClass()
        cls._test_body = 'VOID CONTENT'

        cls.test_record = cls.env['mail.test.sms'].with_context(**cls._test_context).create({
            'name': 'Test',
            'customer_id': cls.partner_1.id,
            'mobile_nbr': cls.test_numbers[0],
            'phone_nbr': cls.test_numbers[1],
        })
        cls.test_record = cls._reset_mail_context(cls.test_record)

    def test_message_sms_internals_body(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms('<p>Mega SMS<br/>Top moumoutte</p>', partner_ids=self.partner_1.ids)

        self.assertEqual(messages.body, '<p>Mega SMS<br>Top moumoutte</p>')
        self.assertEqual(messages.subtype_id, self.env.ref('mail.mt_note'))
        self.assertSMSNotification([{'partner': self.partner_1}], 'Mega SMS\nTop moumoutte', messages)

    def test_message_sms_internals_check_existing(self):
        with self.with_user('employee'), self.mockSMSGateway(sim_error='wrong_number_format'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.partner_1.ids)

        self.assertSMSNotification([{'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_number_format'}], self._test_body, messages)

        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            test_record._notify_record_by_sms(messages, [{'id': self.partner_1.id, 'notif': 'sms'}], check_existing=True)
        self.assertSMSNotification([{'partner': self.partner_1}], self._test_body, messages)

    def test_message_sms_internals_sms_numbers(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.partner_1.ids, sms_numbers=self.random_numbers)

        self.assertSMSNotification([{'partner': self.partner_1}, {'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_internals_subtype(self):
        with self.with_user('employee'), self.mockSMSGateway():
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
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids, sms_pid_to_number=pid_to_number)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'number': self.random_numbers_san[0]},
            {'partner': self.partner_2, 'number': self.random_numbers_san[1]}],
            self._test_body, messages)

    def test_message_sms_model_partner(self):
        with self.with_user('employee'), self.mockSMSGateway():
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
        with self.with_user('employee'):
            record = self.env['mail.test.sms.partner'].create({'customer_id': self.partner_1.id})

            with self.mockSMSGateway():
                messages = record._message_sms(self._test_body)

        self.assertSMSNotification([{'partner': self.partner_1}], self._test_body, messages)

    def test_message_sms_model_w_partner_only_void(self):
        with self.with_user('employee'):
            record = self.env['mail.test.sms.partner'].create({'customer_id': False})

            with self.mockSMSGateway():
                messages = record._message_sms(self._test_body)

        # should not crash but have a failed notification
        self.assertSMSNotification([{'partner': self.env['res.partner'], 'number': False, 'state': 'exception', 'failure_type': 'sms_number_missing'}], self._test_body, messages)

    def test_message_sms_model_w_partner_m2m_only(self):
        with self.with_user('employee'):
            record = self.env['mail.test.sms.partner.2many'].create({'customer_ids': [(4, self.partner_1.id)]})

            with self.mockSMSGateway():
                messages = record._message_sms(self._test_body)

        self.assertSMSNotification([{'partner': self.partner_1}], self._test_body, messages)

        # TDE: should take first found one according to partner ordering
        with self.with_user('employee'):
            record = self.env['mail.test.sms.partner.2many'].create({'customer_ids': [(4, self.partner_1.id), (4, self.partner_2.id)]})

            with self.mockSMSGateway():
                messages = record._message_sms(self._test_body)

        self.assertSMSNotification([{'partner': self.partner_2}], self._test_body, messages)

    def test_message_sms_on_field_w_partner(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, number_field='mobile_nbr')

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_record.mobile_nbr}], self._test_body, messages)

    def test_message_sms_on_field_wo_partner(self):
        self.test_record.write({'customer_id': False})

        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, number_field='mobile_nbr')

        self.assertSMSNotification([{'number': self.test_record.mobile_nbr}], self._test_body, messages)

    def test_message_sms_on_field_wo_partner_wo_value(self):
        """ Test record without a partner and without phone values. """
        self.test_record.write({
            'customer_id': False,
            'phone_nbr': False,
            'mobile_nbr': False,
        })

        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body)

        # should not crash but have a failed notification
        self.assertSMSNotification([{'partner': self.env['res.partner'], 'number': False, 'state': 'exception', 'failure_type': 'sms_number_missing'}], self._test_body, messages)

    def test_message_sms_on_field_wo_partner_default_field(self):
        self.test_record.write({'customer_id': False})

        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body)

        self.assertSMSNotification([{'number': self.test_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_field_wo_partner_default_field_2(self):
        self.test_record.write({'customer_id': False, 'phone_nbr': False})

        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body)

        self.assertSMSNotification([{'number': self.test_numbers_san[0]}], self._test_body, messages)

    def test_message_sms_on_numbers(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, sms_numbers=self.random_numbers_san)
        self.assertSMSNotification([{'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_numbers_sanitization(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, sms_numbers=self.random_numbers)
        self.assertSMSNotification([{'number': self.random_numbers_san[0]}, {'number': self.random_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_partner_ids(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids)

        self.assertSMSNotification([{'partner': self.partner_1}, {'partner': self.partner_2}], self._test_body, messages)

    def test_message_sms_on_partner_ids_default(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body)

        self.assertSMSNotification([{'partner': self.test_record.customer_id, 'number': self.test_numbers_san[1]}], self._test_body, messages)

    def test_message_sms_on_partner_ids_w_numbers(self):
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.partner_1.ids, sms_numbers=self.random_numbers[:1])

        self.assertSMSNotification([{'partner': self.partner_1}, {'number': self.random_numbers_san[0]}], self._test_body, messages)

    def test_message_sms_with_template(self):
        sms_template = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear {{ object.display_name }} this is an SMS.',
        })

        with self.with_user('employee'):
            with self.mockSMSGateway():
                test_record = self.env['mail.test.sms'].browse(self.test_record.id)
                messages = test_record._message_sms_with_template(template=sms_template)

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_numbers_san[1]}], 'Dear %s this is an SMS.' % self.test_record.display_name, messages)

    def test_message_sms_with_template_fallback(self):
        with self.with_user('employee'):
            with self.mockSMSGateway():
                test_record = self.env['mail.test.sms'].browse(self.test_record.id)
                messages = test_record._message_sms_with_template(template_xmlid='test_mail_full.this_should_not_exists', template_fallback='Fallback for {{ object.id }}')

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_numbers_san[1]}], 'Fallback for %s' % self.test_record.id, messages)

    def test_message_sms_with_template_xmlid(self):
        sms_template = self.env['sms.template'].create({
            'name': 'Test Template',
            'model_id': self.env['ir.model']._get('mail.test.sms').id,
            'body': 'Dear {{ object.display_name }} this is an SMS.',
        })
        self.env['ir.model.data'].create({
            'name': 'this_should_exists',
            'module': 'test_mail_full',
            'model': sms_template._name,
            'res_id': sms_template.id,
        })

        with self.with_user('employee'):
            with self.mockSMSGateway():
                test_record = self.env['mail.test.sms'].browse(self.test_record.id)
                messages = test_record._message_sms_with_template(template_xmlid='test_mail_full.this_should_exists')

        self.assertSMSNotification([{'partner': self.partner_1, 'number': self.test_numbers_san[1]}], 'Dear %s this is an SMS.' % self.test_record.display_name, messages)


class TestSMSPostException(TestMailFullCommon, TestMailFullRecipients):

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
        with self.with_user('employee'), self.mockSMSGateway():
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
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.test_record.customer_id.ids)

        self.assertSMSNotification([{'partner': self.test_record.customer_id}], self._test_body, messages)

    def test_message_sms_w_partners_falsy(self):
        # TDE FIXME: currently sent to IAP
        self.test_record.customer_id.write({
            'mobile': 'youpie',
            'phone': 'youpla',
        })
        with self.with_user('employee'), self.mockSMSGateway():
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=self.test_record.customer_id.ids)

        # self.assertSMSNotification({self.test_record.customer_id: {}}, {}, self._test_body, messages)

    def test_message_sms_w_numbers_sanitization_duplicate(self):
        pass
        # TDE FIXME: not sure
        # random_numbers = self.random_numbers + [self.random_numbers[1]]
        # random_numbers_san = self.random_numbers_san + [self.random_numbers_san[1]]
        # with self.with_user('employee'), self.mockSMSGateway():
        #     messages = self.test_record._message_sms(self._test_body, sms_numbers=random_numbers)
        # self.assertSMSNotification({}, {random_numbers_san[0]: {}, random_numbers_san[1]: {}, random_numbers_san[2]: {}}, self._test_body, messages)

    def test_message_sms_crash_credit(self):
        with self.with_user('employee'), self.mockSMSGateway(sim_error='credit'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_credit'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_credit'},
        ], self._test_body, messages)

    def test_message_sms_crash_credit_single(self):
        with self.with_user('employee'), self.mockSMSGateway(nbr_t_error={self.partner_2.phone_get_sanitized_number(): 'credit'}):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2 | self.partner_3).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'sent'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_credit'},
            {'partner': self.partner_3, 'state': 'sent'},
        ], self._test_body, messages)

    def test_message_sms_crash_server_crash(self):
        with self.with_user('employee'), self.mockSMSGateway(sim_error='jsonrpc_exception'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2 | self.partner_3).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_server'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_server'},
            {'partner': self.partner_3, 'state': 'exception', 'failure_type': 'sms_server'},
        ], self._test_body, messages)

    def test_message_sms_crash_unregistered(self):
        with self.with_user('employee'), self.mockSMSGateway(sim_error='unregistered'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_acc'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_acc'},
        ], self._test_body, messages)

    def test_message_sms_crash_unregistered_single(self):
        with self.with_user('employee'), self.mockSMSGateway(nbr_t_error={self.partner_2.phone_get_sanitized_number(): 'unregistered'}):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2 | self.partner_3).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'sent'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_acc'},
            {'partner': self.partner_3, 'state': 'sent'},
        ], self._test_body, messages)

    def test_message_sms_crash_wrong_number(self):
        with self.with_user('employee'), self.mockSMSGateway(sim_error='wrong_number_format'):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'exception', 'failure_type': 'sms_number_format'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_number_format'},
        ], self._test_body, messages)

    def test_message_sms_crash_wrong_number_single(self):
        with self.with_user('employee'), self.mockSMSGateway(nbr_t_error={self.partner_2.phone_get_sanitized_number(): 'wrong_number_format'}):
            test_record = self.env['mail.test.sms'].browse(self.test_record.id)
            messages = test_record._message_sms(self._test_body, partner_ids=(self.partner_1 | self.partner_2 | self.partner_3).ids)

        self.assertSMSNotification([
            {'partner': self.partner_1, 'state': 'sent'},
            {'partner': self.partner_2, 'state': 'exception', 'failure_type': 'sms_number_format'},
            {'partner': self.partner_3, 'state': 'sent'},
        ], self._test_body, messages)


class TestSMSApi(TestMailFullCommon):

    @classmethod
    def setUpClass(cls):
        super(TestSMSApi, cls).setUpClass()
        cls._test_body = 'Zizisse an SMS.'

        cls._create_records_for_batch('mail.test.sms', 3)
        cls.sms_template = cls._create_sms_template('mail.test.sms')

    def test_message_schedule_sms(self):
        with self.with_user('employee'):
            with self.mockSMSGateway():
                self.env['mail.test.sms'].browse(self.records.ids)._message_sms_schedule_mass(body=self._test_body, mass_keep_log=False)

        for record in self.records:
            self.assertSMSOutgoing(record.customer_id, None, content=self._test_body)

    def test_message_schedule_sms_w_log(self):
        with self.with_user('employee'):
            with self.mockSMSGateway():
                self.env['mail.test.sms'].browse(self.records.ids)._message_sms_schedule_mass(body=self._test_body, mass_keep_log=True)

        for record in self.records:
            self.assertSMSOutgoing(record.customer_id, None, content=self._test_body)
            self.assertSMSLogged(record, self._test_body)

    def test_message_schedule_sms_w_template(self):
        with self.with_user('employee'):
            with self.mockSMSGateway():
                self.env['mail.test.sms'].browse(self.records.ids)._message_sms_schedule_mass(template=self.sms_template, mass_keep_log=False)

        for record in self.records:
            self.assertSMSOutgoing(record.customer_id, None, content='Dear %s this is an SMS.' % record.display_name)

    def test_message_schedule_sms_w_template_and_log(self):
        with self.with_user('employee'):
            with self.mockSMSGateway():
                self.env['mail.test.sms'].browse(self.records.ids)._message_sms_schedule_mass(template=self.sms_template, mass_keep_log=True)

        for record in self.records:
            self.assertSMSOutgoing(record.customer_id, None, content='Dear %s this is an SMS.' % record.display_name)
            self.assertSMSLogged(record, 'Dear %s this is an SMS.' % record.display_name)

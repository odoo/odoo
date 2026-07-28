# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from ast import literal_eval

from odoo.addons.phone_validation.tools import phone_validation
from odoo.addons.test_mass_mailing.tests.common import TestMassSMSCommon
from odoo import exceptions
from odoo.tests import tagged
from odoo.tests.common import users
from odoo.tools import mute_logger


@tagged('mass_mailing', 'mass_mailing_sms')
class TestMassSMSInternals(TestMassSMSCommon):

    @users('user_marketing')
    def test_mass_sms_domain(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'Xmas Spam',
            'subject': 'Xmas Spam',
            'mailing_model_id': self.env['ir.model']._get('mail.test.sms').id,
            'mailing_type': 'sms',
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [])

        mailing = self.env['mailing.mailing'].create({
            'name': 'Xmas Spam',
            'subject': 'Xmas Spam',
            'mailing_model_id': self.env['ir.model']._get('mail.test.sms.bl').id,
            'mailing_type': 'sms',
        })
        self.assertEqual(literal_eval(mailing.mailing_domain), [('phone_sanitized_blacklisted', '=', False)])

    @users('user_marketing')
    def test_mass_sms_internals(self):
        with self.with_user('user_marketing'):
            mailing = self.env['mailing.mailing'].create({
                'name': 'Xmas Spam',
                'subject': 'Xmas Spam',
                'mailing_model_id': self.env['ir.model']._get('mail.test.sms').id,
                'mailing_type': 'sms',
                'mailing_domain': '%s' % repr([('name', 'ilike', 'MassSMSTest')]),
                'sms_template_id': self.sms_template.id,
                'sms_allow_unsubscribe': False,
            })

            self.assertEqual(mailing.mailing_model_real, 'mail.test.sms')
            self.assertEqual(mailing.medium_id, self.env.ref('mass_mailing_sms.utm_medium_sms'))
            self.assertEqual(mailing.body_plaintext, self.sms_template.body)

            remaining_res_ids = mailing._get_remaining_recipients()
            self.assertEqual(set(remaining_res_ids), set(self.records.ids))

            with self.mockSMSGateway():
                mailing.action_send_sms()

        self.assertSMSTraces(
            [{'partner': record.customer_id,
              'number': self.records_numbers[i],
              'content': 'Dear %s this is a mass SMS.' % record.display_name
             } for i, record in enumerate(self.records)],
            mailing, self.records,
        )

    @users('user_marketing')
    def test_mass_sms_internals_errors(self):
        # same customer, specific different number on record -> should be valid
        new_record_1 = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_nr1',
            'customer_id': self.partners[0].id,
            'phone_nbr': '0456999999',
        })
        void_record = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_void',
            'customer_id': False,
            'phone_nbr': '',
        })
        falsy_record_1 = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_falsy_1',
            'customer_id': False,
            'phone_nbr': 'abcd',
        })
        falsy_record_2 = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_falsy_2',
            'customer_id': False,
            'phone_nbr': '04561122',
        })
        bl_record_1 = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_bl_1',
            'customer_id': False,
            'phone_nbr': '0456110011',
        })
        self.env['phone.blacklist'].sudo().create({'number': '0456110011'})
        # new customer, number already on record -> should be ignored
        country_be_id = self.env.ref('base.be').id
        nr2_partner = self.env['res.partner'].create({
            'name': 'Partner_nr2',
            'country_id': country_be_id,
            'mobile': '0456449999',
        })
        new_record_2 = self.env['mail.test.sms'].create({
            'name': 'MassSMSTest_nr2',
            'customer_id': nr2_partner.id,
            'phone_nbr': self.records[0].phone_nbr,
        })
        records_numbers = self.records_numbers + ['+32456999999']

        mailing = self.env['mailing.mailing'].browse(self.mailing_sms.ids)
        mailing.write({'sms_force_send': False})  # force outgoing sms, not sent
        with self.with_user('user_marketing'):
            with self.mockSMSGateway():
                mailing.action_send_sms()

        self.assertSMSTraces(
            [{'partner': record.customer_id, 'number': records_numbers[i],
              'content': 'Dear %s this is a mass SMS' % record.display_name}
             for i, record in enumerate(self.records | new_record_1)],
            mailing, self.records | new_record_1,
        )
        # duplicates
        self.assertSMSTraces(
            [{'partner': new_record_2.customer_id, 'number': self.records_numbers[0],
              'content': 'Dear %s this is a mass SMS' % new_record_2.display_name, 'trace_status': 'cancel',
              'failure_type': 'sms_duplicate'}],
            mailing, new_record_2,
        )
        # blacklist
        self.assertSMSTraces(
            [{'partner': self.env['res.partner'], 'number': phone_validation.phone_format(bl_record_1.phone_nbr, 'BE', '32', force_format='E164'),
              'content': 'Dear %s this is a mass SMS' % bl_record_1.display_name, 'trace_status': 'cancel',
              'failure_type': 'sms_blacklist'}],
            mailing, bl_record_1,
        )
        # missing number
        self.assertSMSTraces(
            [{'partner': self.env['res.partner'], 'number': False,
              'content': 'Dear %s this is a mass SMS' % void_record.display_name, 'trace_status': 'cancel',
              'failure_type': 'sms_number_missing'}],
            mailing, void_record,
        )
        # wrong values
        self.assertSMSTraces(
            [{'partner': self.env['res.partner'], 'number': record.phone_nbr,
              'content': 'Dear %s this is a mass SMS' % record.display_name, 'trace_status': 'cancel',
              'failure_type': 'sms_number_format'}
             for record in falsy_record_1 + falsy_record_2],
            mailing, falsy_record_1 + falsy_record_2,
        )

    @users('user_marketing')
    def test_mass_sms_internals_done_ids(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_sms.ids)
        mailing.write({'sms_force_send': False})  # check with outgoing traces, not already pending

        with self.with_user('user_marketing'):
            with self.mockSMSGateway():
                mailing.action_send_sms(res_ids=self.records[:5].ids)

        traces = self.env['mailing.trace'].search([('mass_mailing_id', 'in', mailing.ids)])
        self.assertEqual(len(traces), 5)
        # new traces generated
        self.assertSMSTraces(
            [{'partner': record.customer_id, 'number': self.records_numbers[i],
              'content': 'Dear %s this is a mass SMS' % record.display_name}
             for i, record in enumerate(self.records[:5])],
            mailing, self.records[:5],
        )

        with self.with_user('user_marketing'):
            with self.mockSMSGateway():
                mailing.action_send_sms(res_ids=self.records.ids)

        # delete old traces (for testing purpose: ease check by deleting old ones)
        traces.unlink()
        # new failed traces generated for duplicates
        self.assertSMSTraces(
            [{'partner': record.customer_id, 'number': self.records_numbers[i],
              'content': 'Dear %s this is a mass SMS' % record.display_name, 'trace_status': 'cancel',
              'failure_type': 'sms_duplicate'}
             for i, record in enumerate(self.records[:5])],
            mailing, self.records[:5],
        )
        # new traces generated
        self.assertSMSTraces(
            [{'partner': record.customer_id, 'number': self.records_numbers[i+5],
              'content': 'Dear %s this is a mass SMS' % record.display_name}
             for i, record in enumerate(self.records[5:])],
            mailing, self.records[5:],
        )

    @users('user_marketing')
    def test_mass_sms_processing_with_force_send(self):
        """Test that a `processing` status returned by IAP is immediately applied to traces and mailing stays sending.

        The status update case where the sms are sent via the cron is done in TestSmsController.
        """
        with self.with_user('user_marketing'):
            mailing = self.env['mailing.mailing'].create({
                'name': 'Xmas Spam',
                'subject': 'Xmas Spam',
                'mailing_model_id': self.env['ir.model']._get('mail.test.sms').id,
                'mailing_type': 'sms',
                'mailing_domain': '%s' % repr([('name', 'ilike', 'MassSMSTest')]),
                'sms_template_id': self.sms_template.id,
                'sms_allow_unsubscribe': False,
            })

            remaining_res_ids = mailing._get_remaining_recipients()
            self.assertEqual(set(remaining_res_ids), set(self.records.ids))

            mailing.sms_force_send = True
            with self.mockSMSGateway(moderated=True):
                mailing.action_send_sms()

        self.assertEqual(mailing.state, 'sending')
        self.assertSMSTraces(
            [{'partner': record.customer_id,
              'number': self.records_numbers[i],
              'content': 'Dear %s this is a mass SMS.' % record.display_name,
              'trace_status': 'process',
              } for i, record in enumerate(self.records)],
            mailing, self.records,
        )

    @users('user_marketing')
    def test_mass_sms_error_with_force_send(self):
        """Test that a failed status returned by IAP is immediately applied to traces."""
        with self.with_user('user_marketing'):
            mailing = self.env['mailing.mailing'].create({
                'name': 'Xmas Spam',
                'subject': 'Xmas Spam',
                'mailing_model_id': self.env['ir.model']._get('mail.test.sms').id,
                'mailing_type': 'sms',
                'mailing_domain': '%s' % repr([('name', 'ilike', 'MassSMSTest')]),
                'sms_template_id': self.sms_template.id,
                'sms_allow_unsubscribe': False,
            })

            remaining_res_ids = mailing._get_remaining_recipients()
            self.assertEqual(set(remaining_res_ids), set(self.records.ids))

            mailing.sms_force_send = True
            with self.mockSMSGateway(sim_error='server_error'):
                mailing.action_send_sms()

        self.assertSMSTraces(
            [{'partner': record.customer_id,
              'number': self.records_numbers[i],
              'content': 'Dear %s this is a mass SMS.' % record.display_name,
              'trace_status': 'error',
              'failure_type': 'sms_server'
              } for i, record in enumerate(self.records)],
            mailing, self.records,
        )

    @mute_logger('odoo.addons.mail.models.mail_render_mixin')
    def test_mass_sms_test_button(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestButton',
            'subject': 'Subject {{ object.name }}',
            'preview': 'Preview {{ object.name }}',
            'state': 'draft',
            'mailing_type': 'sms',
            'body_plaintext': 'Hello {{ object.name }}',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        mailing_test = self.env['mailing.sms.test'].with_user(self.user_marketing).create({
            'numbers': '+32456001122',
            'mailing_id': mailing.id,
        })

        with self.with_user('user_marketing'):
            with self.mockSMSGateway():
                mailing_test.action_send_sms()

        # Test if bad inline_template in the body raises an error
        mailing.write({
            'body_plaintext': 'Hello {{ object.name_id.id }}',
        })

        with self.with_user('user_marketing'):
            with self.mock_mail_gateway(), self.assertRaises(Exception):
                mailing_test.action_send_sms()


@tagged('mass_mailing', 'mass_mailing_sms')
class TestMassSMS(TestMassSMSCommon):

    @users('user_marketing')
    def test_mass_sms_links(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_sms.ids)
        mailing.write({
            'body_plaintext': 'Dear {{ object.display_name }} this is a mass SMS with two links http://www.odoo.com/smstest and http://www.odoo.com/smstest/{{ object.name }}',
            'sms_template_id': False,
            'sms_force_send': True,
            'sms_allow_unsubscribe': True,
        })

        with self.mockSMSGateway():
            mailing.action_send_sms()

        self.assertSMSTraces(
            [{'partner': record.customer_id,
              'number': self.records_numbers[i],
              'trace_status': 'pending',
              'content': 'Dear %s this is a mass SMS with two links' % record.display_name
             } for i, record in enumerate(self.records)],
            mailing, self.records,
            sms_links_info=[[
                ('http://www.odoo.com/smstest', True, {}),
                ('http://www.odoo.com/smstest/%s' % record.name, True, {}),
                # unsubscribe is not shortened and parsed at sending
                ('unsubscribe', False, {}),
            ] for record in self.records],
        )

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mass_sms_partner_only(self):
        """ Check sending SMS marketing on models having only a partner_id fields
        set is working. """
        mailing = self.env['mailing.mailing'].browse(self.mailing_sms.ids)
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mail.test.sms.partner').id,
        })

        records = self.env['mail.test.sms.partner'].create([
            {'name': 'MassSMSTest on %s' % partner.name,
             'customer_id': partner.id,
            } for partner in self.partners
        ])

        with self.mockSMSGateway():
            mailing.action_send_sms()

        self.assertEqual(len(mailing.mailing_trace_ids), 10)
        self.assertSMSTraces(
            [{'partner': record.customer_id,
              'number': record.customer_id.phone_sanitized,
              'trace_status': 'pending',
              'content': 'Dear %s this is a mass SMS with two links' % record.display_name
             } for record in records],
            mailing, records,
            sms_links_info=[[
                ('http://www.odoo.com/smstest', True, {}),
                ('http://www.odoo.com/smstest/%s' % record.id, True, {}),
                # unsubscribe is not shortened and parsed at sending
                ('unsubscribe', False, {}),
            ] for record in records],
        )

        # add a new record, send -> sent list should not resend traces
        new_record = self.env['mail.test.sms.partner'].create([
            {'name': 'Duplicate SMS on %s' % self.partners[0].name,
             'customer_id': self.partners[0].id,
            }
        ])
        with self.mockSMSGateway():
            mailing.action_send_sms()

        self.assertEqual(len(mailing.mailing_trace_ids), 11)
        self.assertSMSTraces(
            [{'partner': new_record.customer_id,
              'number': new_record.customer_id.phone_sanitized,
              'trace_status': 'pending',
              'content': 'Dear %s this is a mass SMS with two links' % new_record.display_name
             }],
            mailing, new_record,
            sms_links_info=[[
                ('http://www.odoo.com/smstest', True, {}),
                ('http://www.odoo.com/smstest/%s' % new_record.id, True, {}),
                # unsubscribe is not shortened and parsed at sending
                ('unsubscribe', False, {}),
            ]],
        )

    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mass_sms_partner_only_m2m(self):
        """ Check sending SMS marketing on models having only a m2m to partners
        is currently not suppored. """
        mailing = self.env['mailing.mailing'].browse(self.mailing_sms.ids)
        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mail.test.sms.partner.2many').id,
        })

        self.env['mail.test.sms.partner.2many'].create([
            {'name': 'MassSMSTest on %s' % partner.name,
             'customer_ids': [(4, partner.id)],
            } for partner in self.partners
        ])

        with self.assertRaises(exceptions.UserError), self.mockSMSGateway():
            mailing.action_send_sms()


    @users('user_marketing')
    @mute_logger('odoo.addons.mail.models.mail_mail')
    def test_mass_sms_w_opt_out(self):
        mailing = self.env['mailing.mailing'].browse(self.mailing_sms.ids)
        recipients = self._create_mailing_sms_test_records(model='mail.test.sms.bl.optout', count=5)

        # optout records 0 and 1
        (recipients[0] | recipients[1]).write({'opt_out': True})
        # blacklist records 4
        # TDE FIXME: sudo should not be necessary
        self.env['phone.blacklist'].sudo().create({'number': recipients[4].phone_nbr})

        mailing.write({
            'mailing_model_id': self.env['ir.model']._get('mail.test.sms.bl.optout'),
            'mailing_domain': [('id', 'in', recipients.ids)],
        })

        with self.mockSMSGateway():
            mailing.action_send_sms()

        self.assertSMSTraces(
            [{'number': '+32456000000', 'trace_status': 'cancel', 'failure_type': 'sms_optout'},
             {'number': '+32456000101', 'trace_status': 'cancel', 'failure_type': 'sms_optout'},
             {'number': '+32456000202', 'trace_status': 'pending'},
             {'number': '+32456000303', 'trace_status': 'pending'},
             {'number': '+32456000404', 'trace_status': 'cancel', 'failure_type': 'sms_blacklist'}],
            mailing, recipients
        )
        self.assertEqual(mailing.canceled, 3)

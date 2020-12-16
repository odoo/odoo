# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests.common import TestMassMailCommon
from odoo.addons.test_mass_mailing.data.mail_test_data import MAIL_TEMPLATE
from odoo.tests.common import users
from odoo.tools import mute_logger


class TestMailingInternals(TestMassMailCommon):

    def setUp(self):
        super(TestMailingInternals, self).setUp()

        self.env['ir.config_parameter'].set_param('mail.bounce.alias', 'bounce.test')
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', 'catchall.test')
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'test.example.com')

        self.test_alias = self.env['mail.alias'].create({
            'alias_name': 'test.alias',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mailing.test.simple').id,
            'alias_contact': 'everyone'
        })

    @mute_logger('odoo.addons.mail.models.mail_render_mixin')
    def test_mailing_test_button(self):
        mailing = self.env['mailing.mailing'].create({
            'name': 'TestButton',
            'subject': 'Subject ${object.name}',
            'preview': 'Preview ${object.name}',
            'state': 'draft',
            'mailing_type': 'mail',
            'body_html': '<p>Hello ${object.name}</p>',
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
        })
        mailing_test = self.env['mailing.mailing.test'].create({
            'email_to': 'test@test.com',
            'mass_mailing_id': mailing.id,
        })

        with self.mock_mail_gateway():
            mailing_test.send_mail_test()

        # Test if bad jinja in the subject raises an error
        mailing.write({'subject': 'Subject ${object.name_id.id}'})
        with self.mock_mail_gateway(), self.assertRaises(Exception):
                mailing_test.send_mail_test()

        # Test if bad jinja in the body raises an error
        mailing.write({
            'subject': 'Subject ${object.name}',
            'body_html': '<p>Hello ${object.name_id.id}</p>',
        })
        with self.mock_mail_gateway(), self.assertRaises(Exception):
                mailing_test.send_mail_test()
        
        # Test if bad jinja in the preview raises an error
        mailing.write({
            'body_html': '<p>Hello ${object.name}</p>',
            'preview': 'Preview ${object.name_id.id}',
        })
        with self.mock_mail_gateway(), self.assertRaises(Exception):
                mailing_test.send_mail_test()

    def test_mailing_trace_update(self):
        customers = self.env['res.partner']
        for x in range(0, 3):
            customers |= self.env['res.partner'].create({
                'name': 'Customer_%02d' % x,
                'email': '"Customer_%02d" <customer_%02d@test.example.com' % (x, x),
            })

        mailing = self.env['mailing.mailing'].create({
            'name': 'TestName',
            'subject': 'TestSubject',
            'body_html': 'Hello ${object.name}',
            'reply_to_mode': 'email',
            'reply_to': '%s@%s' % (self.test_alias.alias_name, self.test_alias.alias_domain),
            'keep_archives': True,
            'mailing_model_id': self.env['ir.model']._get('res.partner').id,
            'mailing_domain': '%s' % [('id', 'in', customers.ids)],
        })
        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing.action_send_mail()

        self.gateway_reply_wrecord(MAIL_TEMPLATE, customers[0], use_in_reply_to=True)
        self.gateway_reply_wrecord(MAIL_TEMPLATE, customers[1], use_in_reply_to=False)

        # customer2 looses headers
        mail_mail = self._find_mail_mail_wrecord(customers[2])
        self.format_and_process(
            MAIL_TEMPLATE,
            mail_mail.email_to,
            mail_mail.reply_to,
            subject='Re: %s' % mail_mail.subject,
            extra='',
            msg_id='<123456.%s.%d@test.example.com>' % (customers[2]._name, customers[2].id),
            target_model=customers[2]._name, target_field=customers[2]._rec_name,
        )
        mailing.flush()

        # check traces status
        traces = self.env['mailing.trace'].search([('model', '=', customers._name), ('res_id', 'in', customers.ids)])
        self.assertEqual(len(traces), 3)
        customer0_trace = traces.filtered(lambda t: t.res_id == customers[0].id)
        self.assertEqual(customer0_trace.state, 'replied')
        customer1_trace = traces.filtered(lambda t: t.res_id == customers[1].id)
        self.assertEqual(customer1_trace.state, 'replied')
        customer2_trace = traces.filtered(lambda t: t.res_id == customers[2].id)
        self.assertEqual(customer2_trace.state, 'sent')

        # check mailing statistics
        self.assertEqual(mailing.sent, 3)
        self.assertEqual(mailing.delivered, 3)
        self.assertEqual(mailing.opened, 2)
        self.assertEqual(mailing.replied, 2)

    @users('user_marketing')
    def test_mailing_trace_utm(self):
        """ Test mailing UTMs are caught on reply"""
        self._create_mailing_list()
        self.test_alias.write({
            'alias_model_id': self.env['ir.model']._get('mailing.test.utm').id
        })

        source = self.env['utm.source'].create({'name': 'Source test'})
        medium = self.env['utm.medium'].create({'name': 'Medium test'})
        campaign = self.env['utm.campaign'].create({'name': 'Campaign test'})
        subject = 'MassMailingTestUTM'

        mailing = self.env['mailing.mailing'].create({
            'name': 'UTMTest',
            'subject': subject,
            'body_html': '<p>Hello ${object.name}</p>',
            'reply_to_mode': 'email',
            'reply_to': '%s@%s' % (self.test_alias.alias_name, self.test_alias.alias_domain),
            'keep_archives': True,
            'mailing_model_id': self.env['ir.model']._get('mailing.list').id,
            'contact_list_ids': [(4, self.mailing_list_1.id)],
            'source_id': source.id,
            'medium_id': medium.id,
            'campaign_id': campaign.id
        })

        mailing.action_put_in_queue()
        with self.mock_mail_gateway(mail_unlink_sent=False):
            mailing._process_mass_mailing_queue()

        traces = self.env['mailing.trace'].search([('model', '=', self.mailing_list_1.contact_ids._name), ('res_id', 'in', self.mailing_list_1.contact_ids.ids)])
        self.assertEqual(len(traces), 3)

        # simulate response to mailing
        self.gateway_reply_wrecord(MAIL_TEMPLATE, self.mailing_list_1.contact_ids[0], use_in_reply_to=True)
        self.gateway_reply_wrecord(MAIL_TEMPLATE, self.mailing_list_1.contact_ids[1], use_in_reply_to=False)

        mailing_test_utms = self.env['mailing.test.utm'].search([('name', '=', 'Re: %s' % subject)])
        self.assertEqual(len(mailing_test_utms), 2)
        for test_utm in mailing_test_utms:
            self.assertEqual(test_utm.campaign_id, campaign)
            self.assertEqual(test_utm.source_id, source)
            self.assertEqual(test_utm.medium_id, medium)

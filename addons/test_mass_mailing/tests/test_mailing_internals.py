# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_mass_mailing.tests.common import MassMailingCase
from odoo.addons.test_mass_mailing.data.mail_test_data import MAIL_TEMPLATE


class TestMailingInternals(MassMailingCase):

    def setUp(self):
        super(TestMailingInternals, self).setUp()

        self.env['ir.config_parameter'].set_param('mail.bounce.alias', 'bounce.test')
        self.env['ir.config_parameter'].set_param('mail.catchall.alias', 'catchall.test')
        self.env['ir.config_parameter'].set_param('mail.catchall.domain', 'test.example.com')

        self.test_alias = self.env['mail.alias'].create({
            'alias_name': 'test.alias',
            'alias_user_id': False,
            'alias_model_id': self.env['ir.model']._get('mailing.contact').id,
            'alias_contact': 'everyone'
        })

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
        mailing.action_send_mail()

        self.gateway_reply_wrecord(MAIL_TEMPLATE, customers[0], use_in_reply_to=True)
        self.gateway_reply_wrecord(MAIL_TEMPLATE, customers[1], use_in_reply_to=False)

        # customer2 looses headers
        email = self._find_sent_email_wrecord(customers[2])
        self.format_and_process(
            MAIL_TEMPLATE, email_from=email['email_to'][0], to=email['reply_to'],
            subject='Re: %s' % email['subject'], extra='',
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

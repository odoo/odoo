# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
import random

from odoo.addons.mass_mailing.tests.common import MassMailCommon
from odoo.addons.test_mail.tests.common import TestMailCommon


class TestMassMailCommon(MassMailCommon, TestMailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMassMailCommon, cls).setUpClass()

        # enforce last update by user_marketing to match _process_mass_mailing_queue
        # taking last writer as user running a batch
        cls.mailing_bl = cls.env['mailing.mailing'].with_user(cls.user_marketing).create({
            'name': 'SourceName',
            'subject': 'MailingSubject',
            'body_html': '<p>Hello ${object.name}</p>',
            'mailing_type': 'mail',
            'mailing_model_id': cls.env['ir.model']._get('mailing.test.blacklist').id,
        })

    @classmethod
    def _create_test_blacklist_records(cls, model='mailing.test.blacklist', count=1):
        """ Helper to create data. Currently simple, to be improved. """
        Model = cls.env[model]
        email_field = 'email' if 'email' in Model else 'email_from'

        records = cls.env[model].create([{
            'name': 'TestRecord_%02d' % x,
            email_field: '"TestCustomer %02d" <test.record.%02d@test.example.com>' % (x, x),
        } for x in range(0, count)])
        return records

    @classmethod
    def _create_bounce_trace(cls, record, dt=None):
        if dt is None:
            dt = datetime.datetime.now() - datetime.timedelta(days=1)
        randomized = random.random()
        if 'email_normalized' in record:
            trace_email = record.email_normalized
        elif 'email_from' in record:
            trace_email = record.email_from
        else:
            trace_email = record.email
        trace = cls.env['mailing.trace'].create({
            'model': record._name,
            'res_id': record.id,
            'bounced': dt,
            # TDE FIXME: improve this with a mail-enabled heuristics
            'email': trace_email,
            'message_id': '<%5f@gilbert.boitempomils>' % randomized,
        })
        return trace

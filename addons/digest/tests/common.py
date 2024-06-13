# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import random

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.addons.mail.tests import common as mail_test


class TestDigestCommon(mail_test.MailCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_1 = cls.env.company
        cls.company_2 = cls.env['res.company'].create({'name': 'Digest Company 2'})

        context = {
            'start_datetime': datetime.now() - relativedelta(days=1),
            'end_datetime': datetime.now() + relativedelta(days=1),
        }

        cls.all_digests = cls.env['digest.digest'].with_context(context).create([{
            'name': 'Digest 1',
            'company_id': cls.env.company.id,
            'kpi_mail_message_total': True,
            'kpi_res_users_connected': True,
            'periodicity': 'daily',
        }, {
            'name': 'Digest 2',
            'company_id': cls.company_2.id,
        }, {
            'name': 'Digest 3',
            'company_id': False,
        }])

        cls.digest_1, cls.digest_2, cls.digest_3 = cls.all_digests

    @classmethod
    def _setup_messages(cls):
        """ Remove all existing messages, then create a bunch of them on random
        partners with the correct types in correct time-bucket:

        - 3 in the previous 24h
        - 5 more in the 6 days before that for a total of 8 in the previous week
        - 7 more in the 20 days before *that* (because digest doc lies and is
          based around weeks and months not days), for a total of 15 in the
          previous month
        """
        # regular employee can't necessarily access "private" addresses
        partners = cls.env['res.partner'].search([])
        messages = cls.env['mail.message']
        counter = itertools.count()

        now = fields.Datetime.now()
        for count, (low, high) in [
            (3, (0 * 24, 1 * 24)),
            (5, (1 * 24, 7 * 24)),
            (7, (7 * 24, 27 * 24)),
        ]:
            for __ in range(count):
                create_date = now - relativedelta(hours=random.randint(low + 1, high - 1))
                messages += random.choice(partners).message_post(
                    author_id=cls.partner_admin.id,
                    body=f"Awesome Partner! ({next(counter)})",
                    email_from=cls.partner_admin.email_formatted,
                    message_type='comment',
                    subtype_xmlid='mail.mt_comment',
                    # adjust top and bottom by 1h to avoid overlapping with the
                    # range limit and dropping out of the digest's selection thing
                    create_date=create_date,
                )
        cls.env.flush_all()

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
import random

from datetime import datetime
from dateutil.relativedelta import relativedelta

from odoo import api, Command, fields
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
        cls.kpis = cls.env.ref('digest.kpi_res_users_connected') | cls.env.ref('digest.kpi_mail_message_total')
        cls.kpis.group_ids = cls.env.ref('base.group_user').ids  # Allow internal user to see those kpis for the test
        cls.all_digests = cls.env['digest.digest'].with_context(context).create([{
            'name': 'Digest 1',
            'company_id': cls.env.company.id,
            'periodicity': 'daily',
            'kpi_ids': [Command.link(kpi.id) for kpi in cls.kpis],
        }, {
            'name': 'Digest 2',
            'company_id': cls.company_2.id,
            'kpi_ids': [Command.link(kpi.id) for kpi in cls.kpis],
        }, {
            'name': 'Digest 3',
            'company_id': False,
            'kpi_ids': [Command.link(kpi.id) for kpi in cls.kpis],
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

    def _get_values(self, digests, kpi_name, field_name):
        key_value = 'value'
        if field_name.endswith('_margin'):
            field_name = field_name[:-len('_margin')]
            key_value = 'margin'
        companies = self.env['res.company'].browse([(digest.company_id or digest.env.company).id for digest in digests])
        values_by_kpi_id_by_company_id = digests.digest_kpi_ids.kpi_id._calculate_values_by_company(companies)
        self.assertTrue(all(digest.kpi_ids.filtered(lambda kpi: kpi.name == kpi_name) for digest in digests),
                        f'kpi {kpi_name} must be present in all digest ({digests.mapped("name")})')
        self.assertFalse(any(
            values_by_kpi_id_by_company_id[(digest.company_id or digest.env.company).id][
                digest.kpi_ids.filtered(lambda kpi: kpi.name == kpi_name).id].get('error', False)
            for digest in digests))
        batch_computed = [
            values_by_kpi_id_by_company_id[(digest.company_id or digest.env.company).id][
                digest.kpi_ids.filtered(lambda kpi: kpi.name == kpi_name).id][field_name][key_value]
            for digest in digests
        ]
        # We check that both method leads to the same values
        return batch_computed[0] if len(batch_computed) == 1 else batch_computed

    @api.model
    def _invalidate_digest(self, digests):
        digests.invalidate_recordset()
        digests.digest_kpi_ids.invalidate_recordset()
        digests.kpi_ids.invalidate_recordset()

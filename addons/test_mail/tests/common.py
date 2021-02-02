# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCommon
from odoo.tests.common import TransactionCase


class TestMailCommon(MailCommon):
    """ Main entry point for functional tests. """

    @classmethod
    def _create_channel_listener(cls):
        cls.channel_listen = cls.env['mail.channel'].with_context(cls._test_context).create({'name': 'Listener'})

    @classmethod
    def _create_records_for_batch(cls, model, count):
        # TDE note: to be cleaned in master
        records = cls.env[model]
        partners = cls.env['res.partner']
        country_id = cls.env.ref('base.be').id

        partners = cls.env['res.partner'].with_context(**cls._test_context).create([{
            'name': 'Partner_%s' % (x),
            'email': '_test_partner_%s@example.com' % (x),
            'country_id': country_id,
            'mobile': '047500%02d%02d' % (x, x)
        } for x in range(count)])

        records = cls.env[model].with_context(**cls._test_context).create([{
            'name': 'Test_%s' % (x),
            'customer_id': partners[x].id,
        } for x in range(count)])

        cls.records = cls._reset_mail_context(records)
        cls.partners = partners
        return cls.records, cls.partners


class TestMailMultiCompanyCommon(MailCommon):

    @classmethod
    def setUpClass(cls):
        super(TestMailMultiCompanyCommon, cls).setUpClass()
        cls.company_2 = cls.env['res.company'].create({
            'name': 'Second Test Company',
            'currency_id': 2,
        })


class TestRecipients(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestRecipients, cls).setUpClass()
        Partner = cls.env['res.partner'].with_context({
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
            'no_reset_password': True,
        })
        cls.partner_1 = Partner.create({
            'name': 'Valid Lelitre',
            'email': 'valid.lelitre@agrolait.com',
            'country_id': cls.env.ref('base.be').id,
            'mobile': '0456001122',
        })
        cls.partner_2 = Partner.create({
            'name': 'Valid Poilvache',
            'email': 'valid.other@gmail.com',
            'country_id': cls.env.ref('base.be').id,
            'mobile': '+32 456 22 11 00',
        })

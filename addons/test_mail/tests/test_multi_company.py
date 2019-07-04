# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.urls import url_decode, url_parse
from odoo.tests.common import HttpCase


class TestMultiCompany(HttpCase):

    def test_redirect_to_records(self):

        self.company_A = self.env['res.company'].create({
            'name': 'Company A',
            'user_ids': [(4, self.ref('base.user_admin'))],
        })

        self.company_B = self.env['res.company'].create({
            'name': 'Company B',
        })

        self.multi_company_record = self.env['mail.test.multi.company'].create({
            'name': 'Multi Company Record',
            'company_id': self.company_A.id,
        })

        # Test Case 0
        # Not logged, redirect to web/login
        response = self.url_open('/mail/view?model=%s&res_id=%s' % (
            self.multi_company_record._name,
            self.multi_company_record.id), timeout=15)

        path = url_parse(response.url).path
        self.assertEqual(path, '/web/login')

        self.authenticate('admin', 'admin')

        # Test Case 1
        # Logged into company 1, try accessing record in company A
        # _redirect_to_record should add company A in allowed_company_ids
        response = self.url_open('/mail/view?model=%s&res_id=%s' % (
            self.multi_company_record._name,
            self.multi_company_record.id), timeout=15)

        self.assertEqual(response.status_code, 200)

        fragment = url_parse(response.url).fragment
        cids = url_decode(fragment)['cids']

        self.assertEqual(cids, '1,%s' % (self.company_A.id))

        # Test Case 2
        # Logged into company 1, try accessing record in company B
        # _redirect_to_record should redirect to messaging as the user
        # doesn't have any access for this company
        self.multi_company_record.company_id = self.company_B
        self.multi_company_record.flush()

        response = self.url_open('/mail/view?model=%s&res_id=%s' % (
            self.multi_company_record._name,
            self.multi_company_record.id), timeout=15)

        self.assertEqual(response.status_code, 200)

        fragment = url_parse(response.url).fragment
        action = url_decode(fragment)['action']

        self.assertEqual(action, 'mail.action_discuss')

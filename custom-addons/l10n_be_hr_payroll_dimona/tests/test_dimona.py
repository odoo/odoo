# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date
from unittest.mock import patch
from dateutil.relativedelta import relativedelta

import requests

from odoo.addons.l10n_be_hr_payroll_dimona.models.hr_contract import HrContract
from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install', 'post_install_l10n', 'dimona')
@patch.object(HrContract, '_dimona_authenticate', lambda contract: 'dummy-token')
@patch.object(HrContract, '_cron_l10n_be_check_dimona', lambda contract: True)
class TestDimona(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.belgium = cls.env.ref('base.be')

        cls.env.company.write({
            'country_id': cls.belgium.id,
            'onss_registration_number': '12548245',
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Employee',
            'niss': '93051822361',
            'private_street': '23 Test Street',
            'private_city': 'Test City',
            'private_zip': '6800',
            'private_country_id': cls.belgium.id,
        })

        cls.contract = cls.env['hr.contract'].create({
            'name': 'Test Contract',
            'employee_id': cls.employee.id,
            'wage': 2000,
            'date_start': date.today() + relativedelta(day=1, months=1),
        })

    def test_dimona_open_classic(self):
        wizard = self.env['l10n.be.dimona.wizard'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'declaration_type': 'in',
        })

        def _patched_post(*args, **kwargs):
            response = requests.Response()
            response.headers = {'Location': 'foo/bar/blork/2029409422'}
            response.status_code = 201
            return response

        with patch.object(requests, 'post', _patched_post):
            wizard.submit_declaration()

        self.assertEqual(self.contract.l10n_be_dimona_in_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_last_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_declaration_state, 'waiting')

    def test_dimona_open_foreigner(self):
        self.employee.write({
            'birthday': date(1991, 7, 28),
            'place_of_birth': 'Paris',
            'country_of_birth': self.env.ref('base.fr').id,
            'country_id': self.env.ref('base.fr').id,
            'gender': 'male',
        })

        wizard = self.env['l10n.be.dimona.wizard'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'declaration_type': 'in',
            'without_niss': True,
        })

        def _patched_post(*args, **kwargs):
            response = requests.Response()
            response.headers = {'Location': 'foo/bar/blork/2029409422'}
            response.status_code = 201
            return response

        with patch.object(requests, 'post', _patched_post):
            wizard.submit_declaration()

        self.assertEqual(self.contract.l10n_be_dimona_in_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_last_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_declaration_state, 'waiting')

    def test_dimona_open_student(self):
        self.contract.write({
            'structure_type_id': self.env.ref('l10n_be_hr_payroll.structure_type_student').id,
            'l10n_be_dimona_planned_hours': 130,
            'date_end': date.today() + relativedelta(months=1, day=31),
        })
        wizard = self.env['l10n.be.dimona.wizard'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'declaration_type': 'in',
        })
        def _patched_post(*args, **kwargs):
            response = requests.Response()
            response.headers = {'Location': 'foo/bar/blork/2029409422'}
            response.status_code = 201
            return response

        with patch.object(requests, 'post', _patched_post):
            wizard.submit_declaration()

        self.assertEqual(self.contract.l10n_be_dimona_in_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_last_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_declaration_state, 'waiting')

    def test_dimona_close(self):
        self.contract.write({
            'l10n_be_dimona_in_declaration_number': '2029409422',
            'date_end': date.today() + relativedelta(months=1, day=31),
        })

        wizard = self.env['l10n.be.dimona.wizard'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'declaration_type': 'out',
        })
        def _patched_post(*args, **kwargs):
            response = requests.Response()
            response.headers = {'Location': 'foo/bar/blork/309320239'}
            response.status_code = 201
            return response

        with patch.object(requests, 'post', _patched_post):
            wizard.submit_declaration()

        self.assertEqual(self.contract.l10n_be_dimona_in_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_last_declaration_number, '309320239')
        self.assertEqual(self.contract.l10n_be_dimona_declaration_state, 'waiting')

    def test_dimona_update(self):
        self.contract.write({
            'l10n_be_dimona_in_declaration_number': '2029409422',
            'date_end': date.today() + relativedelta(months=1, day=31),
        })

        wizard = self.env['l10n.be.dimona.wizard'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'declaration_type': 'update',
        })

        def _patched_post(*args, **kwargs):
            response = requests.Response()
            response.headers = {'Location': 'foo/bar/blork/309320239'}
            response.status_code = 201
            return response

        with patch.object(requests, 'post', _patched_post):
            wizard.submit_declaration()

        self.assertEqual(self.contract.l10n_be_dimona_in_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_last_declaration_number, '309320239')
        self.assertEqual(self.contract.l10n_be_dimona_declaration_state, 'waiting')

    def test_dimona_cancel(self):
        self.contract.l10n_be_dimona_in_declaration_number = '2029409422'

        wizard = self.env['l10n.be.dimona.wizard'].create({
            'employee_id': self.employee.id,
            'contract_id': self.contract.id,
            'declaration_type': 'cancel',
        })

        def _patched_post(*args, **kwargs):
            response = requests.Response()
            response.headers = {'Location': 'foo/bar/blork/309320239'}
            response.status_code = 201
            return response

        with patch.object(requests, 'post', _patched_post):
            wizard.submit_declaration()

        self.assertEqual(self.contract.l10n_be_dimona_in_declaration_number, '2029409422')
        self.assertEqual(self.contract.l10n_be_dimona_last_declaration_number, '309320239')
        self.assertEqual(self.contract.l10n_be_dimona_declaration_state, 'waiting')

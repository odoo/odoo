# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase

try:
    from unittest.mock import patch
except ImportError:
    from mock import patch


class TestHrReferralBase(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.company_1 = cls.env['res.company'].create({'name': 'Opoo'})
        cls.company_2 = cls.env['res.company'].create({'name': 'Otoo'})
        cls.company_ids = [cls.company_1.id, cls.company_2.id]

        cls.dep_rd = cls.env['hr.department'].create({
            'name': 'Research and Development',
            'company_id': cls.company_1.id
        })

        # I create a new user "Richard"
        cls.richard_user = cls.env['res.users'].create({
            'name': 'Richard',
            'login': 'ric'
        })

        # I create a new user "Steve"
        cls.steve_user = cls.env['res.users'].create({
            'name': 'Steve',
            'login': 'stv'
        })

        cls.job_dev = cls.env['hr.job'].create({
            'name': 'Dev',
            'no_of_recruitment': '5',
            'department_id': cls.dep_rd.id,
            'company_id': cls.company_1.id,
        })

        cls.mug_shop = cls.env['hr.referral.reward'].create({
            'name': 'Mug',
            'description': 'Beautiful and usefull',
            'cost': '5',
            'company_id': cls.company_1.id,
        })

        cls.red_mug_shop = cls.env['hr.referral.reward'].create({
            'name': 'Red Mug',
            'description': 'It\'s red',
            'cost': '10',
            'company_id': cls.company_2.id,
        })

        cls.mug_shop = cls.mug_shop.with_user(cls.richard_user.id)

    def setUp(self):
        super().setUp()

        def _get_title_from_url(u):
            return "Hello"

        patcher = patch('odoo.addons.link_tracker.models.link_tracker.LinkTracker._get_title_from_url', wraps=_get_title_from_url)
        self.startPatcher(patcher)

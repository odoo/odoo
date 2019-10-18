# -*- coding: utf-8 -*-

from odoo.exceptions import UserError
from odoo.tests import common


class TestCompanyCheck(common.TransactionCase):

    def setUp(self):
        super(TestCompanyCheck, self).setUp()
        self.company_a = self.env['res.company'].create({
            'name': 'Company A'
        })
        self.company_b = self.env['res.company'].create({
            'name': 'Company B'
        })
        self.parent_company_a_id = self.env['test_new_api.model_parent'].create({
            'name': 'M1',
            'company_id': self.company_a.id,
        })
        self.parent_company_b_id = self.env['test_new_api.model_parent'].create({
            'name': 'M2',
            'company_id': self.company_b.id,
        })

    def test_company_check_0(self):
        """ Check the option _check_company_auto is well set on records"""
        m1 = self.env['test_new_api.model_child'].create({'company_id': self.company_a.id})
        self.assertTrue(m1._check_company_auto)

    def test_company_check_1(self):
        """ Check you can create an object if the company are consistent"""
        self.env['test_new_api.model_child'].create({
            'name': 'M1',
            'company_id': self.company_a.id,
            'parent_id': self.parent_company_a_id.id,
        })

    def test_company_check_2(self):
        """ Check you cannot create a record if the company is inconsistent"""
        with self.assertRaises(UserError):
            self.env['test_new_api.model_child'].create({
                'name': 'M1',
                'company_id': self.company_b.id,
                'parent_id': self.parent_company_a_id.id,
            })

    def test_company_check_3(self):
        """ Check you can create a record with the inconsistent company if there are no check"""
        self.env['test_new_api.model_child_nocheck'].create({
            'name': 'M1',
            'company_id': self.company_b.id,
            'parent_id': self.parent_company_a_id.id,
        })

    def test_company_check_4(self):
        """ Check the company consistency is respected at write. """
        child = self.env['test_new_api.model_child'].create({
            'name': 'M1',
            'company_id': self.company_a.id,
            'parent_id': self.parent_company_a_id.id,
        })

        with self.assertRaises(UserError):
            child.company_id = self.company_b.id

        with self.assertRaises(UserError):
            child.parent_id = self.parent_company_b_id.id

        child.write({
            'parent_id': self.parent_company_b_id.id,
            'company_id': self.company_b.id,
        })

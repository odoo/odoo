# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, users, tagged
from odoo.addons.mail.tests.common import mail_new_test_user


class TestProjectProfitabilityCommon(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.partner = cls.env['res.partner'].create({
            'name': 'Georges',
            'email': 'georges@project-profitability.com'})

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan A',
        })
        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Project - AA',
            'code': 'AA-1234',
            'plan_id': cls.analytic_plan.id,
        })
        cls.project = cls.env['project.project'].with_context({'mail_create_nolog': True}).create({
            'name': 'Project',
            'partner_id': cls.partner.id,
            'account_id': cls.analytic_account.id,
        })
        cls.task = cls.env['project.task'].with_context({'mail_create_nolog': True}).create({
            'name': 'Task',
            'project_id': cls.project.id,
        })
        cls.project_profitability_items_empty = {
            'revenues': {'data': [], 'total': {'invoiced': 0.0, 'to_invoice': 0.0}},
            'costs': {'data': [], 'total': {'billed': 0.0, 'to_bill': 0.0}},
        }
        cls.foreign_currency = cls.env['res.currency'].create({
            'name': 'Chaos orb',
            'symbol': '☺',
            'rounding': 0.001,
            'position': 'after',
            'currency_unit_label': 'Chaos',
            'currency_subunit_label': 'orb',
        })
        cls.env['res.currency.rate'].create({
            'name': '2016-01-01',
            'rate': '5.0',
            'currency_id': cls.foreign_currency.id,
        })

class TestProfitability(TestProjectProfitabilityCommon):
    def test_project_profitability(self):
        """ Test the project profitability has no data found

            In this module, the project profitability should have no data.
            So the no revenue and cost should be found.
        """
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'The profitability data of the project should be return no data and so 0 for each total amount.'
        )


@tagged('-at_install', 'post_install')
class TestProjectProfitabilityAccess(TestProjectProfitabilityCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.project_user = mail_new_test_user(cls.env, 'Project User', groups='project.group_project_user')
        cls.project_manager = mail_new_test_user(cls.env, 'Project Admin', groups='project.group_project_manager')

    @users('Project User', 'Project Admin')
    def test_project_profitability_read(self):
        """ Test the project profitability read access rights

            In other modules, project profitability may contain some data.
            The project user and project admin should have read access rights to project profitability.
        """
        self.project.with_user(self.env.user)._get_profitability_items(False)

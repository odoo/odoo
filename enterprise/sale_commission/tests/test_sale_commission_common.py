# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import Command

from odoo.addons.sale.tests.common import TestSaleCommon


class TestSaleCommissionCommon(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.commission_product_1 = cls.env['product.product'].create({
            'name': 'Chocolate Cake',
        })

        cls.commission_product_2 = cls.env['product.product'].create({
            'name': 'Chocolate Cookies',
        })

        cls.env['res.currency.rate'].create({
            'rate': 1,
            'currency_id': cls.env.company.currency_id.id,
            'name': datetime.date(year=2000, month=1, day=1),
        })

        cls.team_commission = cls.env['crm.team'].create({
            'name': 'Team Team',
            'sequence': 1,
            'company_id': cls.env.company.id
        })

        cls.commission_user_1 = cls.env['res.users'].create({
            'login': "Sales 1",
            'partner_id': cls.env['res.partner'].create({
                'name': "Sales 1"
            }).id,
            'groups_id': [Command.set(cls.env.ref('sales_team.group_sale_salesman').ids)],
        })

        cls.commission_user_2 = cls.env['res.users'].create({
            'login': "Sales 2",
            'partner_id': cls.env['res.partner'].create({
                'name': "Sales 2"
            }).id,
            'groups_id': [Command.set(cls.env.ref('sales_team.group_sale_salesman').ids)],
        })

        cls.commission_manager = cls.env['res.users'].create({
            'login': "Manager 1",
            'partner_id': cls.env['res.partner'].create({
                'name': "Manager 1"
            }).id,
            'groups_id': [Command.set(cls.env.ref('sales_team.group_sale_manager').ids)],
        })

        cls.commission_plan_user = cls.env['sale.commission.plan'].create({
            'name': "User",
            'company_id': cls.env.company.id,
            'date_from': datetime.date(year=2024, month=1, day=1),
            'date_to': datetime.date(year=2024, month=12, day=31),
            'periodicity': 'month',
            'type': 'target',
            'user_type': 'person',
            'commission_amount': 2500,
        })

        cls.commission_plan_user.user_ids = cls.env['sale.commission.plan.user'].create([{
            'user_id': cls.commission_user_1.id,
            'plan_id': cls.commission_plan_user.id,
        }, {
            'user_id': cls.commission_user_2.id,
            'plan_id': cls.commission_plan_user.id,
        }])

        cls.commission_plan_manager = cls.env['sale.commission.plan'].create([{
            'name': "Manager",
            'company_id': cls.env.company.id,
            'date_from': datetime.date(year=2024, month=1, day=1),
            'date_to': datetime.date(year=2024, month=12, day=31),
            'periodicity': 'month',
            'type': 'achieve',
            'user_type': 'team',
            'team_id': cls.team_commission.id,
        }])

        cls.commission_plan_manager.user_ids = cls.env['sale.commission.plan.user'].create([{
            'user_id': cls.commission_manager.id,
            'plan_id': cls.commission_plan_manager.id,
        }])

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import Command

from odoo.addons.sale_commission.tests.test_sale_commission_common import TestSaleCommissionCommon
from odoo.addons.sale_subscription.tests.common_sale_subscription import TestSubscriptionCommon


class TestSaleSubscriptionCommissionCommon(TestSaleCommissionCommon, TestSubscriptionCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.commission_plan_sub = cls.env['sale.commission.plan'].create({
            'name': "Subscription Commission (on invoices)",
            'company_id': cls.env.company.id,
            'date_from': datetime.date(year=2024, month=1, day=1),
            'date_to': datetime.date(year=2024, month=12, day=31),
            'periodicity': 'month',
            'type': 'achieve',
            'user_type': 'person',
            'commission_amount': 2500,

        })

        cls.commission_plan_sub.user_ids = cls.env['sale.commission.plan.user'].create([{
            'user_id': cls.commission_user_1.id,
            'plan_id': cls.commission_plan_sub.id,
        }, {
            'user_id': cls.commission_user_2.id,
            'plan_id': cls.commission_plan_sub.id,
        }])


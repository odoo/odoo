# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import tests
from odoo.tests.common import TransactionCase


@tests.tagged('mail_activity_mixin')
class TestMailActivityMixin(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner_model = cls.env['res.partner']

        cls.plan_1, cls.plan_2 = cls.env['mail.activity.plan'].create([{
            'name': 'Plan A',
            'res_model': 'res.partner',
        }, {
            'name': 'Plan B',
            'res_model': 'res.partner',
        }])
        cls.partner_with_plan, cls.partner_without_plan = cls.env['res.partner'].create([{
            'name': 'Partner - With Plan',
        }, {
            'name': 'Partner - With Plan 2',
        }])
        cls.env['mail.activity'].create({
            'res_model_id': cls.env['ir.model']._get_id('res.partner'),
            'res_id': cls.partner_with_plan.id,
            'activity_type_id': cls.env.ref('mail.mail_activity_data_call').id,
            'activity_plan_id': cls.plan_1.id,
        })
        cls.partners = cls.partner_with_plan | cls.partner_without_plan

    def test_activity_plan_ids(self):
        domain_true = self.partner_model._search_activity_plans_ids('in', [True])
        result_true = self.partners.filtered_domain(domain_true)
        self.assertEqual(result_true, self.partner_with_plan)

        domain_specific = self.partner_model._search_activity_plans_ids('in', [self.plan_1.id])
        result_specific = self.partners.filtered_domain(domain_specific)
        self.assertEqual(result_specific, self.partner_with_plan)

        domain_wrong = self.partner_model._search_activity_plans_ids('in', [self.plan_2.id])
        result_wrong = self.partners.filtered_domain(domain_wrong)
        self.assertEqual(result_wrong, self.partner_model)  # Should be empty

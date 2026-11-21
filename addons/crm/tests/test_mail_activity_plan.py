# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError
from odoo.tests import TransactionCase, new_test_user, tagged, users


@tagged('mail_activity', 'mail_activity_plan')
class TestCrmActivityPlan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user_sale_manager = new_test_user(
            cls.env, groups='base.group_user,sales_team.group_sale_manager', login='sale_manager')

    @users('sale_manager')
    def test_plan_manager_access(self):
        """Check access for `mail.activity.plan`.

        The sales managers can manage all the lead plans, whatever their
        users, but not the plans of the other models.
        """
        Plan = self.env['mail.activity.plan']
        other_plan = Plan.sudo().create({
            'name': 'Other Plan',
            'res_model': 'res.partner',
            'template_ids': [Command.create({'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id})],
        }).sudo(False)
        user_admin = self.env.ref('base.user_admin')
        users_list = (self.env['res.users'], user_admin, self.env.user + user_admin)
        for plan_users in users_list:
            with self.subTest(users=plan_users):
                plan = Plan.create({
                    'name': 'Plan',
                    'res_model': 'crm.lead',
                    'template_ids': [Command.create({'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id})],
                    'user_ids': plan_users.ids,
                })
                plan.write({
                    'name': 'Renamed Plan',
                    'template_ids': [Command.create({'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id})],
                    'user_ids': user_admin.ids,
                })
                plan.user_ids = False
                plan.template_ids.summary = 'Renamed Activity'
                with self.assertRaises(AccessError):
                    plan.res_model = 'res.partner'
                with self.assertRaises(AccessError):
                    plan.template_ids.plan_id = other_plan
                plan.template_ids[0].unlink()
                plan.unlink()

        for records in (other_plan, other_plan.template_ids):
            self.assertTrue(records.has_access('read'))
            self.assertFalse(records.has_access('write'))
            self.assertFalse(records.has_access('unlink'))
        self.assertFalse(other_plan.template_ids.has_access('create'))
        for plan_users in users_list:
            with self.subTest(users=plan_users), self.assertRaises(AccessError):
                Plan.create({'name': 'Plan', 'res_model': 'res.partner', 'user_ids': plan_users.ids})

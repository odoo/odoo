from odoo.tests import tagged

from odoo.addons.l10n_ph.tests.common import TestPhCommon


@tagged('post_install_l10n', 'post_install', '-at_install')
class TestPaymentVoucher(TestPhCommon):

    def test_plain_text_analytic_distribution_summary(self):
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        department_plan = self.env['account.analytic.plan'].create({
            'name': 'Department',
        })
        project_account = self.env['account.analytic.account'].create({
            'name': 'Project Alpha',
            'plan_id': project_plan.id,
        })
        department_account_a = self.env['account.analytic.account'].create({
            'name': 'Department A',
            'plan_id': department_plan.id,
        })
        department_account_b = self.env['account.analytic.account'].create({
            'name': 'Department B',
            'plan_id': department_plan.id,
        })

        bill = self.init_invoice(
            move_type='in_invoice',
            amounts=[100.0],
            partner=self.partner_a,
        )
        line = bill.invoice_line_ids
        line.analytic_distribution = {
            f'{project_account.id},{department_account_a.id}': 20.0,
            f'{project_account.id},{department_account_b.id}': 80.0,
        }

        self.assertEqual(
            line._get_analytic_distribution_plain_text(),
            f'{project_account.display_name}\n'
            f'20% {department_account_a.display_name}, 80% {department_account_b.display_name}',
        )

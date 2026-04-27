# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from freezegun import freeze_time

from dateutil.relativedelta import relativedelta
from odoo.addons.hr_payroll.tests.common import TestPayslipBase
from odoo.addons.mail.tests.common import mail_new_test_user


class TestPayslipFlow(TestPayslipBase):

    def test_00_payslip_flow(self):
        """ Testing payslip flow and report printing """
        # activate Richard's contract
        self.richard_emp.contract_ids[0].state = 'open'

        # I create an employee Payslip
        richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id
        })

        payslip_input = self.env['hr.payslip.input'].search([('payslip_id', '=', richard_payslip.id)])
        # I assign the amount to Input data
        payslip_input.write({'amount': 5.0})

        # I verify the payslip is in draft state
        self.assertEqual(richard_payslip.state, 'draft', 'State not changed!')

        richard_payslip.compute_sheet()

        # Then I click on the 'Confirm' button on payslip
        richard_payslip.action_payslip_done()

        # I verify that the payslip is in done state
        self.assertEqual(richard_payslip.state, 'done', 'State not changed!')

        # Then I click on the 'Mark as paid' button on payslip
        richard_payslip.action_payslip_paid()

        # I verify that the payslip is in paid state
        self.assertEqual(richard_payslip.state, 'paid', 'State not changed!')

        # I want to check refund payslip so I click on refund button.
        richard_payslip.refund_sheet()

        # I check on new payslip Credit Note is checked or not.
        payslip_refund = self.env['hr.payslip'].search([('name', 'like', 'Refund: '+ richard_payslip.name), ('credit_note', '=', True)])
        self.assertTrue(bool(payslip_refund), "Payslip not refunded!")

        # I want to generate a payslip from Payslip run.
        payslip_run = self.env['hr.payslip.run'].create({
            'date_end': '2011-09-30',
            'date_start': '2011-09-01',
            'name': 'Payslip for Employee'
        })

        # I create record for generating the payslip for this Payslip run.

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id)]
        })

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

    def test_01_batch_with_specific_structure(self):
        """ Generate payslips for the employee whose running contract is based on the same Salary Structure Type"""

        specific_structure_type = self.env['hr.payroll.structure.type'].create({
            'name': 'Structure Type Test'
        })

        specific_structure = self.env['hr.payroll.structure'].create({
            'name': 'End of the Year Bonus - Test',
            'type_id': specific_structure_type.id,
        })

        self.richard_emp.contract_ids[0].state = 'open'

        # 13th month pay
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'End of the year bonus'
        })
        # I create record for generating the payslip for this Payslip run.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'structure_id': specific_structure.id,
        })

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id)._compute_employee_ids()

        self.assertFalse(payslip_employee.employee_ids)

        # Update the structure type and generate payslips again
        specific_structure_type.default_struct_id = specific_structure.id
        self.richard_emp.contract_ids[0].structure_type_id = specific_structure_type.id

        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'Batch for Structure'
        })

        payslip_employee = self.env['hr.payslip.employees'].create({
            'structure_id': specific_structure.id,
        })

        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id)._compute_employee_ids()

        self.assertTrue(payslip_employee.employee_ids)
        self.assertTrue(self.richard_emp.id in payslip_employee.employee_ids.ids)

        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

        self.assertEqual(len(payslip_run.slip_ids), 1)
        self.assertEqual(payslip_run.slip_ids.struct_id.id, specific_structure.id)

    def test_02_payslip_batch_with_archived_employee(self):
        # activate Richard's contract
        self.richard_emp.contract_ids[0].state = 'open'
        # archive his contact
        self.richard_emp.action_archive()

        # 13th month pay
        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'End of the year bonus'
        })
        # I create record for generating the payslip for this Payslip run.
        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id)],
        })
        # I generate the payslip by clicking on Generat button wizard.
        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()

        self.assertEqual(len(payslip_run.slip_ids), 1)

    def test_03_payslip_batch_with_payment_process(self):
        '''
            Test to check if some payslips in the batch are already paid,
            the batch status can be updated to 'paid' without affecting
            those already paid payslips.
        '''

        self.richard_emp.contract_ids[0].state = 'open'
        self.contract_jules = self.env['hr.contract'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'name': 'Contract for Jules',
            'wage': 5000.33,
            'employee_id': self.jules_emp.id,
            'state': 'open',
        })

        payslip_run = self.env['hr.payslip.run'].create({
            'date_start': datetime.date.today() + relativedelta(years=-1, month=8, day=1),
            'date_end': datetime.date.today() + relativedelta(years=-1, month=8, day=31),
            'name': 'Payment Test'
        })

        payslip_employee = self.env['hr.payslip.employees'].create({
            'employee_ids': [(4, self.richard_emp.id), (4, self.jules_emp.id)],
        })

        payslip_employee.with_context(active_id=payslip_run.id).compute_sheet()
        payslip_run.action_validate()

        self.assertEqual(len(payslip_run.slip_ids), 2)
        self.assertTrue(all(payslip.state == 'done' for payslip in payslip_run.slip_ids), 'State not changed!')

        # Mark the first payslip as paid and store the paid date
        payslip_run.slip_ids[0].action_payslip_paid()
        paid_date = payslip_run.slip_ids[0].paid_date

        self.assertEqual(payslip_run.slip_ids[0].state, 'paid', 'State not changed!')
        self.assertEqual(payslip_run.slip_ids[1].state, 'done', 'State not changed!')

        payslip_run.action_paid()

        self.assertEqual(payslip_run.state, 'paid', 'State not changed!')
        self.assertTrue(all(payslip.state == 'paid' for payslip in payslip_run.slip_ids), 'State not changed!')
        self.assertEqual(payslip_run.slip_ids[0].paid_date, paid_date, 'payslip paid date should not be changed')

    def test_04_payroll_struct_country_change(self):
        """ Testing the write on country_id from payroll structure """
        test_structure = self.env['hr.payroll.structure'].create({
            'name': 'Test Payroll Structure',
            'type_id': self.structure_type.id,
            'country_id': False
        })
        rule_1 = self.env['hr.salary.rule'].create({
            'name': 'Test 1',
            'code': 'T1',
            'category_id': self.env.ref('hr_payroll.BASIC').id,
            'struct_id': test_structure.id,
            'appears_on_payroll_report': True
        })
        rule_2 = self.env['hr.salary.rule'].create({
            'name': 'Test 2',
            'code': 'T2',
            'category_id': self.env.ref('hr_payroll.BASIC').id,
            'struct_id': test_structure.id,
            'appears_on_payroll_report': False
        })

        # Check a field has been created from rule_1 as x_l10n_xx_t1
        self.assertTrue(self.env['ir.model.fields'].search([('name', '=', 'x_l10n_xx_t1')]))

        # Write a new country_id on test_structure
        test_structure.write({'country_id': self.env.ref('base.us').id})

        # Check a new rule field has been created as x_l10n_us_t1
        self.assertTrue(self.env['ir.model.fields'].search([('name', '=', 'x_l10n_us_t1')]))

        # Check x_l10n_xx_t1 has been removed
        self.assertFalse(self.env['ir.model.fields'].search([('name', '=', 'x_l10n_xx_t1')]))

        # Check that the rules appears_on_payroll_report are the same after the write
        self.assertTrue(rule_1.appears_on_payroll_report)
        self.assertFalse(rule_2.appears_on_payroll_report)

    def test_04_cancel_a_done_payslip_with_payroll_admin(self):
        """Cancel a done payslip using a new user with Payroll Admin access."""
        test_user = mail_new_test_user(
            self.env, name="Test user", login="test_user",
            groups="hr_payroll.group_hr_payroll_manager"
        )
        self.richard_emp.contract_ids[0].state = 'open'
        richard_payslip = self.env['hr.payslip'].create({
            'name': 'Payslip of Richard',
            'employee_id': self.richard_emp.id,
        })
        richard_payslip.action_payslip_done()
        self.assertEqual(richard_payslip.state, 'done')
        richard_payslip.with_user(test_user).action_payslip_cancel()
        self.assertEqual(richard_payslip.state, 'cancel')

    @freeze_time('2025-01-15')
    def test_05_batch_with_closed_contract_different_structure(self):
        """Check payslip wizard computes employees taking into account the state
        of the contracts matching the structure type of the wizard. Contracts not
        in open/close state should be ignored."""

        structure_type_a = self.env['hr.payroll.structure.type'].create({
            'name': 'Structure Type A - Test',
        })
        structure_a = self.env['hr.payroll.structure'].create({
            'name': 'Structure A',
            'type_id': structure_type_a.id,
        })
        structure_type_a.default_struct_id = structure_a.id

        structure_type_b = self.env['hr.payroll.structure.type'].create({
            'name': 'Structure Type B - Test',
        })
        structure_b = self.env['hr.payroll.structure'].create({
            'name': 'Structure B',
            'type_id': structure_type_b.id,
        })
        structure_type_b.default_struct_id = structure_b.id

        self.env['hr.contract'].create([
            {
                'date_start': '2024-09-01',
                'name': 'New contract - Structure A',
                'wage': 5000,
                'employee_id': self.richard_emp.id,
                'structure_type_id': structure_type_a.id,
                'state': 'draft',
            },
            {
                'date_start': '2024-12-01',
                'date_end': '2024-12-31',
                'name': 'Old contract (December) - Structure A',
                'wage': 5000,
                'employee_id': self.richard_emp.id,
                'structure_type_id': structure_type_a.id,
                'state': 'close',
            },
            {
                'date_start': '2025-01-01',
                'name': 'Running contract - Structure B',
                'wage': 5000,
                'employee_id': self.richard_emp.id,
                'structure_type_id': structure_type_b.id,
                'state': 'open',
            }
        ])

        payslip_run = self.env['hr.payslip.run'].create({
            'name': 'January batch',
            'date_start': '2025-01-01',
            'date_end': '2025-01-31',
        })
        payslip_wizard = self.env['hr.payslip.employees'].create({
            'structure_id': structure_a.id,
        }).with_context({'active_id': payslip_run.id})

        payslip_wizard._compute_employee_ids()
        self.assertNotIn(self.richard_emp, payslip_wizard.employee_ids, 'Richard has no close/open structure A contract in January')

        payslip_wizard.structure_id = structure_b
        payslip_wizard._compute_employee_ids()
        self.assertIn(self.richard_emp, payslip_wizard.employee_ids, 'Richard has a close/open structure B contract in January')

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import Form, common


class TestResPartnerBank(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

    def test_res_partner_bank_employee_view(self):
        partner_1, partner_2 = self.env['res.partner'].create([{'name': 'Ralph'}, {'name': 'Bella'}])
        self.env['hr.employee'].create([
            {
                'name': 'Ralph',
                'work_contact_id': partner_1.id,
            },
            {
                'name': 'Bella',
                'work_contact_id': partner_2.id,
            }
        ])
        res_partner_bank_1 = self.env['res.partner.bank'].create([{
            'acc_number': '0144748555',
            'partner_id': partner_1.id,
        }])
        partner_bank_form = 'hr_payroll_account.view_partner_bank_form_inherit_hr_payroll_account'
        # This context is set in the act window.
        partner = self.env['res.partner.bank'].with_context(from_employee_bank_account=True)

        with Form(partner, view=partner_bank_form) as partner_bank:
            partner_bank.acc_number = '12111121232'
            partner_bank.partner_id = partner_1
            self.assertTrue(partner_bank.has_alt_bank_account)
            p_bank = partner_bank.save()
            self.assertNotEqual(res_partner_bank_1, partner_1.employee_ids[0].bank_account_id)
            self.assertEqual(p_bank, partner_1.employee_ids[0].bank_account_id)

        self.assertFalse(partner_2.employee_ids[0].bank_account_id)
        with Form(partner, view=partner_bank_form) as partner_bank:
            partner_bank.acc_number = '23298957'
            partner_bank.partner_id = partner_2
            self.assertFalse(partner_bank.has_alt_bank_account)
            p_bank = partner_bank.save()
            self.assertEqual(p_bank, partner_2.employee_ids[0].bank_account_id)
